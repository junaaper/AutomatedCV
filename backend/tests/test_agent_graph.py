import uuid

import pytest
from langgraph.types import Command
from sqlalchemy import func, select

from app.agent import runtime
from app.agent.state import AgentContext
from app.applications.models import AgentRun, Application
from app.auth.models import User
from app.cv.service import ingest_cv
from app.db import SessionLocal
from app.providers.embeddings import HashingEmbedder
from app.providers.fake_llm import OfflineChatModel
from tests.samples import CV_TEXT, POSTING

pytestmark = pytest.mark.usefixtures("db")

CTX = AgentContext(
    llm=OfflineChatModel(), embedder=HashingEmbedder(768), session_factory=SessionLocal
)


@pytest.fixture
async def run_ids():
    """A user with a CV and a run row, as the API would create them."""
    async with SessionLocal() as s:
        user = User(email=f"{uuid.uuid4().hex}@example.com", password_hash="x")
        s.add(user)
        await s.flush()
        run = AgentRun(user_id=user.id)
        s.add(run)
        await s.commit()
        await ingest_cv(s, user.id, CV_TEXT, None, CTX.embedder)
        return str(user.id), str(run.id)


def config(run_id):
    return {"configurable": {"thread_id": run_id}}


async def run_to_review(run_ids):
    user_id, run_id = run_ids
    graph = await runtime.get_graph()
    inp = {"user_id": user_id, "run_id": run_id, "posting": POSTING, "revisions": 0}
    await graph.ainvoke(inp, config(run_id), context=CTX)
    return graph, run_id


async def application_count():
    async with SessionLocal() as s:
        return await s.scalar(select(func.count()).select_from(Application))


async def test_runs_to_review_with_grounded_fit(run_ids):
    graph, run_id = await run_to_review(run_ids)
    snap = await graph.aget_state(config(run_id))

    assert snap.next == ("human_review",)
    [pending] = snap.interrupts
    review = pending.value
    assert review["job"]["company"] == "Initech"
    assert len(review["job"]["must_have"]) == 4

    by_req = {r["requirement"]: r for r in review["fit"]["requirements"]}
    fastapi = next(r for k, r in by_req.items() if "FastAPI" in k)
    k8s = next(r for k, r in by_req.items() if "Kubernetes" in k)
    assert fastapi["verdict"] == "match" and fastapi["evidence_verified"]
    assert k8s["verdict"] == "missing"
    assert 0 < review["fit"]["score"] < 100
    assert "Initech" in review["cover_letter"]
    assert await application_count() == 0  # nothing saved before approval


async def test_approve_saves_application(run_ids):
    graph, run_id = await run_to_review(run_ids)
    result = await graph.ainvoke(Command(resume={"action": "approve"}), config(run_id), context=CTX)
    assert result["decision"] == "approve"
    async with SessionLocal() as s:
        app = await s.get(Application, uuid.UUID(result["application_id"]))
    assert app.company == "Initech" and app.fit_score == result["fit"]["score"]


async def test_edit_saves_users_letter(run_ids):
    graph, run_id = await run_to_review(run_ids)
    result = await graph.ainvoke(
        Command(resume={"action": "edit", "cover_letter": "My own words."}),
        config(run_id),
        context=CTX,
    )
    async with SessionLocal() as s:
        app = await s.get(Application, uuid.UUID(result["application_id"]))
    assert app.cover_letter == "My own words."


async def test_revise_redrafts_and_pauses_again(run_ids):
    graph, run_id = await run_to_review(run_ids)
    await graph.ainvoke(
        Command(resume={"action": "revise", "feedback": "Mention billing"}),
        config(run_id),
        context=CTX,
    )
    snap = await graph.aget_state(config(run_id))
    assert snap.next == ("human_review",)
    assert snap.values["revisions"] == 1
    assert "Mention billing" in snap.interrupts[0].value["cover_letter"]
    assert await application_count() == 0


async def test_reject_ends_without_saving(run_ids):
    graph, run_id = await run_to_review(run_ids)
    result = await graph.ainvoke(Command(resume={"action": "reject"}), config(run_id), context=CTX)
    assert result["decision"] == "reject"
    assert (await graph.aget_state(config(run_id))).next == ()
    assert await application_count() == 0


async def test_paused_run_survives_restart(run_ids):
    """Simulates Render sleeping: drop the graph and its pool, rebuild, then resume."""
    _, run_id = await run_to_review(run_ids)
    await runtime.close_graph()

    fresh = await runtime.get_graph()
    snap = await fresh.aget_state(config(run_id))
    assert snap.next == ("human_review",)
    result = await fresh.ainvoke(Command(resume={"action": "approve"}), config(run_id), context=CTX)
    assert result["application_id"]
