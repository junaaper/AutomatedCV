import re
import uuid

from langgraph.graph import END
from langgraph.runtime import Runtime
from langgraph.types import Command, interrupt
from sqlalchemy import select

from app.agent import prompts
from app.agent.llm_json import invoke_json, invoke_text
from app.agent.schemas import (
    AssessedRequirement,
    FitAssessmentLLM,
    FitResult,
    JobRequirements,
    fit_score,
)
from app.agent.state import AgentContext, AgentError, AgentState
from app.applications.models import Application
from app.cv.service import search_cv

EVIDENCE_PER_REQUIREMENT = 3


async def extract_requirements(state: AgentState, runtime: Runtime[AgentContext]) -> AgentState:
    job = await invoke_json(
        runtime.context.llm,
        prompts.EXTRACT_REQUIREMENTS,
        prompts.wrap_input({"posting": state["posting"]}),
        JobRequirements,
    )
    if not job.all_requirements():
        raise AgentError("Couldn't find any requirements in that posting.")
    return {"job": job.model_dump()}


async def retrieve_evidence(state: AgentState, runtime: Runtime[AgentContext]) -> AgentState:
    """Tool step: semantic search over the user's CV chunks for every requirement."""
    requirements = [r for r, _ in JobRequirements(**state["job"]).all_requirements()]
    async with runtime.context.session_factory() as session:
        hits = await search_cv(
            session,
            uuid.UUID(state["user_id"]),
            requirements,
            runtime.context.embedder,
            k=EVIDENCE_PER_REQUIREMENT,
        )
    return {
        "evidence": {
            req: [
                {"chunk_id": str(h.chunk_id), "content": h.content, "similarity": h.similarity}
                for h in req_hits
            ]
            for req, req_hits in zip(requirements, hits, strict=True)
        }
    }


def _normalise(text: str) -> str:
    text = re.sub(r"(?<!\w)\.|\.(?!\w)", " ", text.lower())  # keep dots only inside "node.js"
    return " ".join(re.sub(r"[^\w+#%.]+", " ", text).split())


def quote_is_grounded(quote: str, excerpts: list[str]) -> bool:
    """True if the quote really appears in the retrieved excerpts (whitespace/punctuation
    insensitive). This is the agent's guard against hallucinated evidence."""
    q = _normalise(quote)
    return len(q) >= 3 and any(q in _normalise(e) for e in excerpts)


async def score_fit(state: AgentState, runtime: Runtime[AgentContext]) -> AgentState:
    requirements = JobRequirements(**state["job"]).all_requirements()
    excerpts = {
        req: [e["content"] for e in state["evidence"].get(req, [])] for req, _ in requirements
    }
    payload = {
        "requirements": [
            {"requirement": req, "kind": kind, "excerpts": excerpts[req]}
            for req, kind in requirements
        ]
    }
    out = await invoke_json(
        runtime.context.llm, prompts.SCORE_FIT, prompts.wrap_input(payload), FitAssessmentLLM
    )

    assessed = []
    for i, (req, kind) in enumerate(requirements):
        # Align by position; our requirement text wins over the model's echo of it.
        a = out.assessments[i] if i < len(out.assessments) else None
        verdict = a.verdict if a else "missing"
        evidence = a.evidence if a else None
        grounded = bool(evidence) and quote_is_grounded(evidence, excerpts[req])
        if not grounded:
            evidence = None
            if verdict == "match":  # a claimed match with no real quote is downgraded
                verdict = "partial"
        assessed.append(
            AssessedRequirement(
                requirement=req,
                kind=kind,
                verdict=verdict,
                evidence=evidence,
                evidence_verified=grounded,
                reasoning=a.reasoning if a else "Not assessed by the model.",
            )
        )
    fit = FitResult(
        score=fit_score(assessed),
        requirements=assessed,
        strengths=out.strengths[:5],
        gaps=out.gaps[:5],
    )
    return {"fit": fit.model_dump()}


async def draft_cover_letter(state: AgentState, runtime: Runtime[AgentContext]) -> AgentState:
    fit = state["fit"]
    payload = {
        "job": state["job"],
        "fit": {
            "score": fit["score"],
            # Only grounded evidence goes to the writer, so it can't cite invented facts.
            "requirements": [
                {k: r[k] for k in ("requirement", "kind", "verdict", "evidence")}
                for r in fit["requirements"]
            ],
            "gaps": fit["gaps"],
        },
    }
    if state.get("feedback"):
        payload["previous_draft"] = state.get("cover_letter", "")
        payload["feedback"] = state["feedback"]
    letter = await invoke_text(
        runtime.context.llm, prompts.DRAFT_COVER_LETTER, prompts.wrap_input(payload)
    )
    if not letter:
        raise AgentError("The model returned an empty cover letter.")
    return {"cover_letter": letter, "feedback": None}


def review_payload(state: AgentState, max_revisions: int) -> dict:
    revisions = state.get("revisions", 0)
    return {
        "job": state["job"],
        "fit": state["fit"],
        "evidence": state["evidence"],
        "cover_letter": state["cover_letter"],
        "revisions": revisions,
        "can_revise": revisions < max_revisions,
    }


async def human_review(state: AgentState, runtime: Runtime[AgentContext]) -> Command:
    """Pauses the graph. The checkpoint is saved to Postgres, so the pause survives the
    server sleeping; the API resumes it with Command(resume={...}).

    The resume payload is validated by the API before resuming."""
    decision = interrupt(review_payload(state, runtime.context.max_revisions))
    match decision["action"]:
        case "approve":
            return Command(goto="save_application", update={"decision": "approve"})
        case "edit":
            return Command(
                goto="save_application",
                update={"decision": "edit", "cover_letter": decision["cover_letter"]},
            )
        case "revise":
            return Command(
                goto="draft_cover_letter",
                update={
                    "feedback": decision["feedback"],
                    "revisions": state.get("revisions", 0) + 1,
                },
            )
        case _:
            return Command(goto=END, update={"decision": "reject"})


async def save_application(state: AgentState, runtime: Runtime[AgentContext]) -> AgentState:
    job, fit = state["job"], state["fit"]
    run_id = uuid.UUID(state["run_id"])
    async with runtime.context.session_factory() as session:
        # Idempotent: if we crashed after committing but before the checkpoint was written,
        # a retry finds the row instead of inserting a duplicate.
        existing = await session.scalar(select(Application.id).where(Application.run_id == run_id))
        if existing:
            return {"application_id": str(existing)}
        app = Application(
            user_id=uuid.UUID(state["user_id"]),
            run_id=run_id,
            title=job["title"][:200],
            company=job["company"][:200],
            posting=state["posting"],
            requirements=job,
            fit=fit,
            fit_score=fit["score"],
            cover_letter=state["cover_letter"],
        )
        session.add(app)
        await session.commit()
        return {"application_id": str(app.id)}
