"""Agent run API. Runs stream progress to the browser as Server-Sent Events.

The graph executes in a background task that pushes events into a queue; the SSE
response just relays them. If the browser disconnects, the run still finishes and
records its status, so reloading the page picks up where it left off.
"""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_core.language_models import BaseChatModel
from langgraph.types import Command
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select, update

from app.agent.llm_json import LLMOutputError
from app.agent.nodes import review_payload
from app.agent.runtime import get_graph
from app.agent.state import AgentContext, AgentError
from app.applications.models import AgentRun, RunStatus
from app.auth.deps import CurrentUser
from app.auth.models import User
from app.config import get_settings
from app.cv.models import CvChunk
from app.db import SessionDep, SessionLocal
from app.demo.service import embedder_for, is_replayed, llm_for
from app.limits.quota import consume_llm_run
from app.limits.ratelimit import rate_limit
from app.providers.embeddings import Embedder, get_embedder
from app.providers.llm import get_llm

log = logging.getLogger(__name__)
router = APIRouter(prefix="/runs", tags=["agent"])

# A "running" run not updated for this long was killed (e.g. the server slept or
# restarted mid-run). It can be retried from its last checkpoint.
STALE_AFTER = timedelta(minutes=5)

# Holds references so background runs aren't garbage-collected mid-flight.
_background: set[asyncio.Task] = set()


# --- request / response models ---


class StartRun(BaseModel):
    posting: str = Field(min_length=100, max_length=20_000)


class ResumeRun(BaseModel):
    action: Literal["approve", "edit", "revise", "reject"]
    cover_letter: str | None = Field(default=None, max_length=10_000)
    feedback: str | None = Field(default=None, max_length=1_000)

    @model_validator(mode="after")
    def _check_fields(self) -> "ResumeRun":
        if self.action == "edit" and not (self.cover_letter or "").strip():
            raise ValueError("cover_letter is required to edit")
        if self.action == "revise" and not (self.feedback or "").strip():
            raise ValueError("feedback is required to revise")
        return self


class RunSummary(BaseModel):
    id: uuid.UUID
    status: RunStatus
    title: str | None
    company: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime
    retryable: bool


class RunDetail(RunSummary):
    state: dict[str, Any]
    review: dict[str, Any] | None


# --- helpers ---


def _context(user: User, posting: str, llm: BaseChatModel, embedder: Embedder) -> AgentContext:
    return AgentContext(
        llm=llm_for(user, posting, llm),
        embedder=embedder_for(user, embedder),
        session_factory=SessionLocal,
        max_revisions=get_settings().max_revisions,
    )


def _config(run_id: uuid.UUID) -> dict:
    return {"configurable": {"thread_id": str(run_id)}}


def _is_retryable(run: AgentRun) -> bool:
    stale = run.status == RunStatus.running and datetime.now(UTC) - run.updated_at > STALE_AFTER
    return run.status == RunStatus.failed or stale


def _summary(run: AgentRun) -> dict:
    return {
        "id": run.id,
        "status": run.status,
        "title": run.title,
        "company": run.company,
        "error": run.error,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "retryable": _is_retryable(run),
    }


async def _owned_run(session, run_id: uuid.UUID, user_id: uuid.UUID) -> AgentRun:
    run = await session.get(AgentRun, run_id)
    if run is None or run.user_id != user_id:  # don't reveal other users' run ids
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    return run


async def _claim(session, run_id: uuid.UUID, user_id: uuid.UUID, allowed: list[RunStatus]) -> None:
    """Atomically flips the run to `running`, so double-clicks can't resume it twice."""
    result = await session.execute(
        update(AgentRun)
        .where(AgentRun.id == run_id, AgentRun.user_id == user_id, AgentRun.status.in_(allowed))
        .values(status=RunStatus.running, error=None, updated_at=func.now())
    )
    await session.commit()
    if result.rowcount == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "Run is not in a state that allows this")


def _step_summary(node: str, update: dict) -> dict:
    match node:
        case "extract_requirements":
            job = update["job"]
            return {
                "title": job["title"],
                "company": job["company"],
                "requirements": len(job["must_have"]) + len(job["nice_to_have"]),
            }
        case "retrieve_evidence":
            return {"chunks": sum(len(v) for v in update["evidence"].values())}
        case "score_fit":
            return {"score": update["fit"]["score"]}
        case "save_application":
            return {"application_id": update["application_id"]}
        case _:
            return {}


async def _set_run(run_id: uuid.UUID, **values) -> None:
    async with SessionLocal() as s:
        await s.execute(
            update(AgentRun).where(AgentRun.id == run_id).values(**values, updated_at=func.now())
        )
        await s.commit()


async def _drive(
    graph_input: Any, run_id: uuid.UUID, ctx: AgentContext, queue: asyncio.Queue
) -> None:
    """Runs the graph to its next pause or end, emitting events, then records status."""
    graph = await get_graph()
    try:
        async for chunk in graph.astream(
            graph_input, _config(run_id), context=ctx, stream_mode="updates"
        ):
            for node, update_ in chunk.items():
                if node == "__interrupt__":
                    continue  # reported once, below, from the saved state
                summary = _step_summary(node, update_ or {})
                if node == "extract_requirements":
                    await _set_run(
                        run_id, title=summary["title"][:200], company=summary["company"][:200]
                    )
                else:
                    await _set_run(run_id)  # heartbeat for stale detection
                await queue.put(("step", {"node": node, **summary}))

        snap = await graph.aget_state(_config(run_id))
        if snap.interrupts:
            await _set_run(run_id, status=RunStatus.awaiting_review)
            await queue.put(("review", snap.interrupts[0].value))
        elif snap.values.get("decision") == "reject":
            await _set_run(run_id, status=RunStatus.rejected)
            await queue.put(("done", {"status": RunStatus.rejected}))
        else:
            await _set_run(run_id, status=RunStatus.completed)
            await queue.put(
                (
                    "done",
                    {
                        "status": RunStatus.completed,
                        "application_id": snap.values.get("application_id"),
                    },
                )
            )
    except Exception as exc:
        if isinstance(exc, AgentError):
            message = str(exc)
        elif isinstance(exc, LLMOutputError):
            message = "The AI model returned something unusable. Try again."
        else:
            log.exception("Agent run %s failed", run_id)
            message = "Something went wrong while running the agent. Try again."
        await _set_run(run_id, status=RunStatus.failed, error=message)
        await queue.put(("error", {"message": message, "retryable": True}))
    finally:
        await queue.put(None)


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _stream(graph_input: Any, run_id: uuid.UUID, ctx: AgentContext) -> StreamingResponse:
    queue: asyncio.Queue = asyncio.Queue()
    task = asyncio.create_task(_drive(graph_input, run_id, ctx, queue))
    _background.add(task)
    task.add_done_callback(_background.discard)

    async def events() -> AsyncIterator[str]:
        yield _sse("run", {"run_id": str(run_id)})
        while (item := await queue.get()) is not None:
            yield _sse(*item)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


LLMDep = Annotated[BaseChatModel, Depends(get_llm)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]


# --- endpoints ---


@router.post(
    "", response_class=StreamingResponse, dependencies=[rate_limit("run-start", 6, by="user")]
)
async def start_run(
    body: StartRun, user: CurrentUser, session: SessionDep, llm: LLMDep, embedder: EmbedderDep
) -> StreamingResponse:
    """Start analysing a posting. Streams `run`, `step`..., then `review` | `error`."""
    has_cv = await session.scalar(select(CvChunk.id).where(CvChunk.user_id == user.id).limit(1))
    if not has_cv:
        raise HTTPException(status.HTTP_409_CONFLICT, "Upload your CV before analysing a job.")
    if not is_replayed(user, body.posting):
        await consume_llm_run(session, user)
    run = AgentRun(user_id=user.id)
    session.add(run)
    await session.commit()
    graph_input = {"user_id": str(user.id), "run_id": str(run.id), "posting": body.posting}
    ctx = _context(user, body.posting, llm, embedder)
    return _stream({**graph_input, "revisions": 0}, run.id, ctx)


@router.post(
    "/{run_id}/resume",
    response_class=StreamingResponse,
    dependencies=[rate_limit("run-step", 20, by="user")],
)
async def resume_run(
    run_id: uuid.UUID,
    body: ResumeRun,
    user: CurrentUser,
    session: SessionDep,
    llm: LLMDep,
    embedder: EmbedderDep,
) -> StreamingResponse:
    """Answer the review pause: approve, edit (with cover_letter), revise (with
    feedback), or reject."""
    await _owned_run(session, run_id, user.id)
    values = (await (await get_graph()).aget_state(_config(run_id))).values
    posting = values.get("posting", "")
    if body.action == "revise":
        if values.get("revisions", 0) >= get_settings().max_revisions:
            raise HTTPException(status.HTTP_409_CONFLICT, "Revision limit reached")
        if not is_replayed(user, posting, body.feedback):
            await consume_llm_run(session, user)  # only revise calls the model
    await _claim(session, run_id, user.id, [RunStatus.awaiting_review])
    ctx = _context(user, posting, llm, embedder)
    return _stream(Command(resume=body.model_dump(exclude_none=True)), run_id, ctx)


@router.post(
    "/{run_id}/retry",
    response_class=StreamingResponse,
    dependencies=[rate_limit("run-step", 20, by="user")],
)
async def retry_run(
    run_id: uuid.UUID, user: CurrentUser, session: SessionDep, llm: LLMDep, embedder: EmbedderDep
) -> StreamingResponse:
    """Continue a failed or interrupted run from its last checkpoint (completed steps
    are not repeated)."""
    run = await _owned_run(session, run_id, user.id)
    if not _is_retryable(run):
        raise HTTPException(status.HTTP_409_CONFLICT, "Run is not retryable")
    posting = (await (await get_graph()).aget_state(_config(run_id))).values.get("posting", "")
    if not is_replayed(user, posting):
        await consume_llm_run(session, user)
    await _claim(session, run_id, user.id, [RunStatus.failed, RunStatus.running])
    return _stream(None, run_id, _context(user, posting, llm, embedder))


@router.get("")
async def list_runs(user: CurrentUser, session: SessionDep) -> list[RunSummary]:
    runs = await session.scalars(
        select(AgentRun)
        .where(AgentRun.user_id == user.id)
        .order_by(AgentRun.created_at.desc())
        .limit(50)
    )
    return [RunSummary(**_summary(r)) for r in runs]


@router.get("/{run_id}")
async def get_run(run_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> RunDetail:
    """Full run state, including the pending review, so a reload (or a server that slept)
    restores the review screen exactly."""
    run = await _owned_run(session, run_id, user.id)
    snap = await (await get_graph()).aget_state(_config(run_id))
    values = snap.values or {}
    state = {
        k: values.get(k)
        for k in ("job", "evidence", "fit", "cover_letter", "revisions", "application_id")
    }
    review = (
        review_payload(values, get_settings().max_revisions)
        if run.status == RunStatus.awaiting_review and snap.interrupts
        else None
    )
    return RunDetail(**_summary(run), state=state, review=review)
