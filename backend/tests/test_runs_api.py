import json

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.main import app
from app.providers.llm import get_llm
from tests.conftest import signup_headers
from tests.samples import CV_TEXT, POSTING

pytestmark = pytest.mark.usefixtures("db")


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


@pytest.fixture
async def user(client, auth_headers):
    resp = await client.post("/cv", data={"text": CV_TEXT}, headers=auth_headers)
    assert resp.status_code == 201
    return auth_headers


async def start(client, headers, posting=POSTING):
    resp = await client.post("/runs", json={"posting": posting}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(resp.text)
    return events[0][1]["run_id"], events


async def resume(client, headers, run_id, **body):
    return await client.post(f"/runs/{run_id}/resume", json=body, headers=headers)


async def test_start_requires_cv(client, auth_headers):
    resp = await client.post("/runs", json={"posting": POSTING}, headers=auth_headers)
    assert resp.status_code == 409


async def test_start_validates_posting_length(client, user):
    resp = await client.post("/runs", json={"posting": "too short"}, headers=user)
    assert resp.status_code == 422


async def test_full_flow_stream_review_approve_then_track(client, user):
    run_id, events = await start(client, user)
    kinds = [e for e, _ in events]
    assert kinds == ["run", "step", "step", "step", "step", "review"]
    steps = [d["node"] for e, d in events if e == "step"]
    assert steps == ["extract_requirements", "retrieve_evidence", "score_fit", "draft_cover_letter"]
    assert events[1][1]["company"] == "Initech"
    review = events[-1][1]
    assert review["can_revise"] and review["cover_letter"]

    # Reload: the review is restorable from the API alone.
    detail = (await client.get(f"/runs/{run_id}", headers=user)).json()
    assert detail["status"] == "awaiting_review"
    assert detail["title"] == "Senior Backend Engineer"
    assert detail["review"]["cover_letter"] == review["cover_letter"]

    done = parse_sse((await resume(client, user, run_id, action="approve")).text)
    assert done[-1][0] == "done" and done[-1][1]["status"] == "completed"
    app_id = done[-1][1]["application_id"]

    apps = (await client.get("/applications", headers=user)).json()
    assert [a["id"] for a in apps] == [app_id]
    patched = await client.patch(
        f"/applications/{app_id}", json={"status": "applied", "notes": "Sent"}, headers=user
    )
    assert patched.json()["status"] == "applied" and patched.json()["notes"] == "Sent"
    assert (await client.delete(f"/applications/{app_id}", headers=user)).status_code == 204
    assert (await client.get("/applications", headers=user)).json() == []

    # A finished run can't be resumed again.
    assert (await resume(client, user, run_id, action="approve")).status_code == 409


async def test_revise_then_edit(client, user):
    run_id, _ = await start(client, user)
    revised = parse_sse(
        (await resume(client, user, run_id, action="revise", feedback="Shorter")).text
    )
    assert revised[-1][0] == "review" and revised[-1][1]["revisions"] == 1

    done = parse_sse((await resume(client, user, run_id, action="edit", cover_letter="Mine.")).text)
    app_id = done[-1][1]["application_id"]
    detail = (await client.get(f"/applications/{app_id}", headers=user)).json()
    assert detail["cover_letter"] == "Mine."


async def test_reject(client, user):
    run_id, _ = await start(client, user)
    done = parse_sse((await resume(client, user, run_id, action="reject")).text)
    assert done[-1] == ("done", {"status": "rejected"})
    assert (await client.get("/applications", headers=user)).json() == []


async def test_resume_payload_validation(client, user):
    run_id, _ = await start(client, user)
    assert (await resume(client, user, run_id, action="edit")).status_code == 422
    assert (await resume(client, user, run_id, action="revise", feedback=" ")).status_code == 422
    assert (await resume(client, user, run_id, action="explode")).status_code == 422


async def test_runs_are_private(client, user):
    run_id, _ = await start(client, user)
    other = await signup_headers(client, "other@example.com")
    assert (await client.get(f"/runs/{run_id}", headers=other)).status_code == 404
    assert (await resume(client, other, run_id, action="approve")).status_code == 404
    assert (await client.get("/runs", headers=other)).json() == []
    assert len((await client.get("/runs", headers=user)).json()) == 1


async def test_llm_failure_marks_run_failed_and_retry_continues(client, user):
    app.dependency_overrides[get_llm] = lambda: FakeListChatModel(responses=["not json"] * 2)
    try:
        run_id, events = await start(client, user)
    finally:
        app.dependency_overrides.pop(get_llm)
    assert events[-1][0] == "error" and events[-1][1]["retryable"]
    detail = (await client.get(f"/runs/{run_id}", headers=user)).json()
    assert detail["status"] == "failed" and detail["retryable"]

    resp = await client.post(f"/runs/{run_id}/retry", headers=user)
    retried = parse_sse(resp.text)
    assert retried[-1][0] == "review"
    assert (await client.get(f"/runs/{run_id}", headers=user)).json()["status"] == "awaiting_review"
