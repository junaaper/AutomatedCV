from datetime import UTC, datetime, timedelta

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import func, select, update

from app.applications.models import Application
from app.auth.models import User
from app.db import SessionLocal
from app.demo.content import REVISION_SUGGESTIONS, SAMPLE_POSTINGS
from app.demo.replay import MissingRecording, ReplayChatModel
from app.demo.service import create_demo_user, load_fixtures, purge_expired_demo_users
from app.main import app
from app.providers.llm import get_llm
from tests.conftest import CAPTCHA_FAIL_TOKEN
from tests.test_runs_api import parse_sse

pytestmark = pytest.mark.usefixtures("db")

FINTECH = next(s for s in SAMPLE_POSTINGS if s.id == "senior-backend-fintech")


class LLMDown(BaseChatModel):
    """Simulates the free LLM API being unavailable."""

    @property
    def _llm_type(self) -> str:
        return "down"

    def _generate(self, *a, **kw):
        raise ConnectionError("LLM API unavailable")

    async def _agenerate(self, *a, **kw):
        raise ConnectionError("LLM API unavailable")


@pytest.fixture
def llm_down():
    app.dependency_overrides[get_llm] = lambda: LLMDown()
    yield
    app.dependency_overrides.pop(get_llm)


async def demo_headers(client):
    resp = await client.post("/auth/demo", json={"turnstile_token": "ok"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["user"]["is_demo"] is True
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_every_sample_posting_has_a_complete_recording():
    fixtures = load_fixtures()
    for sample in SAMPLE_POSTINGS:
        responses = fixtures[sample.id]["responses"]
        assert {"extract_requirements", "score_fit", "draft_cover_letter"} <= set(responses)
        for fb in REVISION_SUGGESTIONS:
            assert f"draft_cover_letter:{fb.lower()}" in responses


async def test_replay_model_raises_without_recording_or_fallback():
    model = ReplayChatModel(responses={})
    with pytest.raises(MissingRecording):
        model.invoke([SystemMessage("TASK: score_fit"), HumanMessage("<input>{}</input>")])


async def test_postings_endpoint_is_public(client):
    resp = await client.get("/demo/postings")
    assert [p["id"] for p in resp.json()] == [s.id for s in SAMPLE_POSTINGS]


async def test_demo_login_requires_captcha(client):
    resp = await client.post("/auth/demo", json={"turnstile_token": CAPTCHA_FAIL_TOKEN})
    assert resp.status_code == 400


async def test_demo_account_comes_seeded(client):
    headers = await demo_headers(client)
    cv = (await client.get("/cv", headers=headers)).json()
    assert cv["content"].startswith("Sam Rivera")
    apps = (await client.get("/applications", headers=headers)).json()
    assert {a["status"] for a in apps} == {"interviewing", "applied"}


async def test_demo_run_works_with_the_llm_api_down(client, llm_down):
    headers = await demo_headers(client)
    resp = await client.post("/runs", json={"posting": FINTECH.posting}, headers=headers)
    events = parse_sse(resp.text)
    assert events[-1][0] == "review", events[-1]
    review = events[-1][1]
    expected = load_fixtures()[FINTECH.id]["snapshot"]
    assert review["job"]["company"] == "Northwind Pay"
    assert review["fit"]["score"] == expected["fit"]["score"]  # quotes still ground on replay
    run_id = events[0][1]["run_id"]

    chip = await client.post(
        f"/runs/{run_id}/resume",
        json={"action": "revise", "feedback": REVISION_SUGGESTIONS[0]},
        headers=headers,
    )
    revised = parse_sse(chip.text)[-1]
    assert revised[0] == "review" and revised[1]["revisions"] == 1

    done = parse_sse(
        (
            await client.post(f"/runs/{run_id}/resume", json={"action": "approve"}, headers=headers)
        ).text
    )
    assert done[-1][1]["status"] == "completed"


async def test_unrecorded_feedback_falls_back_to_the_live_model(client, llm_down):
    headers = await demo_headers(client)
    events = parse_sse(
        (await client.post("/runs", json={"posting": FINTECH.posting}, headers=headers)).text
    )
    run_id = events[0][1]["run_id"]
    resp = await client.post(
        f"/runs/{run_id}/resume",
        json={"action": "revise", "feedback": "Mention my open-source library"},
        headers=headers,
    )
    assert parse_sse(resp.text)[-1][0] == "error"  # live model is down -> retryable error


async def test_custom_posting_uses_the_live_model(client, llm_down):
    headers = await demo_headers(client)
    custom = FINTECH.posting.replace("Northwind Pay", "Some Other Co")
    events = parse_sse((await client.post("/runs", json={"posting": custom}, headers=headers)).text)
    assert events[-1][0] == "error"


async def test_expired_demo_users_are_purged():
    async with SessionLocal() as s:
        fresh = await create_demo_user(s)
        old = await create_demo_user(s)
        await s.execute(
            update(User)
            .where(User.id == old.id)
            .values(created_at=datetime.now(UTC) - timedelta(hours=25))
        )
        await s.commit()
        assert await purge_expired_demo_users(s) == 1
        remaining = (await s.scalars(select(User.id).where(User.is_demo))).all()
        assert remaining == [fresh.id]
        orphaned = await s.scalar(
            select(func.count()).select_from(Application).where(Application.user_id == old.id)
        )
        assert orphaned == 0
