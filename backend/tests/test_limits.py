import pytest

from app.config import get_settings
from app.demo.content import SAMPLE_POSTINGS
from app.limits.ratelimit import RateLimiter
from tests.samples import CV_TEXT, POSTING
from tests.test_runs_api import parse_sse

pytestmark = pytest.mark.usefixtures("db")


async def test_sliding_window():
    rl = RateLimiter()
    assert rl.hit("k", 2, 60) is None
    assert rl.hit("k", 2, 60) is None
    retry = rl.hit("k", 2, 60)
    assert retry is not None and 0 < retry <= 60
    assert rl.hit("other", 2, 60) is None  # keys are independent


async def test_login_is_rate_limited_per_ip(client):
    body = {"email": "x@example.com", "password": "whatever-pass", "turnstile_token": "ok"}
    codes = [(await client.post("/auth/login", json=body)).status_code for _ in range(11)]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429
    resp = await client.post("/auth/login", json=body)
    assert int(resp.headers["Retry-After"]) > 0


@pytest.fixture
async def user_with_cv(client, auth_headers):
    await client.post("/cv", data={"text": CV_TEXT}, headers=auth_headers)
    return auth_headers


@pytest.fixture
def daily_limit(monkeypatch):
    def set_limits(user: int = 20, demo: int = 3, global_: int = 500):
        s = get_settings()
        monkeypatch.setattr(s, "daily_llm_runs_per_user", user)
        monkeypatch.setattr(s, "demo_daily_llm_runs", demo)
        monkeypatch.setattr(s, "global_daily_llm_runs", global_)

    return set_limits


async def test_daily_quota_blocks_extra_runs_and_reports_usage(client, user_with_cv, daily_limit):
    daily_limit(user=1)
    first = await client.post("/runs", json={"posting": POSTING}, headers=user_with_cv)
    assert parse_sse(first.text)[-1][0] == "review"

    second = await client.post("/runs", json={"posting": POSTING}, headers=user_with_cv)
    assert second.status_code == 429
    assert "today's 1 AI runs" in second.json()["detail"]

    usage = (await client.get("/usage", headers=user_with_cv)).json()
    assert usage["used"] == 1 and usage["limit"] == 1


async def test_approving_is_free_but_revising_counts(client, user_with_cv, daily_limit):
    daily_limit(user=2)
    run_id = parse_sse(
        (await client.post("/runs", json={"posting": POSTING}, headers=user_with_cv)).text
    )[0][1]["run_id"]
    revise = await client.post(
        f"/runs/{run_id}/resume", json={"action": "revise", "feedback": "x"}, headers=user_with_cv
    )
    assert parse_sse(revise.text)[-1][0] == "review"
    over = await client.post(
        f"/runs/{run_id}/resume", json={"action": "revise", "feedback": "y"}, headers=user_with_cv
    )
    assert over.status_code == 429
    approve = await client.post(
        f"/runs/{run_id}/resume", json={"action": "approve"}, headers=user_with_cv
    )
    assert parse_sse(approve.text)[-1][1]["status"] == "completed"


async def test_global_cap_protects_the_api_key(client, user_with_cv, daily_limit):
    daily_limit(global_=0)
    resp = await client.post("/runs", json={"posting": POSTING}, headers=user_with_cv)
    assert resp.status_code == 429
    assert "shared AI budget" in resp.json()["detail"]


async def test_replayed_demo_runs_dont_use_quota(client, daily_limit):
    daily_limit(demo=0, global_=0)
    headers = {
        "Authorization": "Bearer "
        + (await client.post("/auth/demo", json={"turnstile_token": "ok"})).json()["access_token"]
    }
    sample = await client.post(
        "/runs", json={"posting": SAMPLE_POSTINGS[0].posting}, headers=headers
    )
    assert parse_sse(sample.text)[-1][0] == "review"
    custom = await client.post("/runs", json={"posting": POSTING}, headers=headers)
    assert custom.status_code == 429
