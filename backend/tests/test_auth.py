import pytest
from sqlalchemy import select

from app.auth.models import RefreshToken, User
from app.db import SessionLocal
from tests.conftest import CAPTCHA_FAIL_TOKEN

pytestmark = pytest.mark.usefixtures("db")

EMAIL = "Ada@Example.com"
PASSWORD = "correct horse battery"


async def signup(client, email=EMAIL, password=PASSWORD, captcha="ok"):
    return await client.post(
        "/auth/signup", json={"email": email, "password": password, "turnstile_token": captcha}
    )


async def login(client, email=EMAIL, password=PASSWORD, captcha="ok"):
    return await client.post(
        "/auth/login", json={"email": email, "password": password, "turnstile_token": captcha}
    )


def bearer(resp):
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_signup_returns_token_sets_cookie_and_stores_argon2_hash(client):
    resp = await signup(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["email"] == "ada@example.com"  # normalised
    assert body["user"]["is_demo"] is False
    cookie = resp.headers["set-cookie"]
    assert "refresh_token=" in cookie and "HttpOnly" in cookie and "Path=/auth" in cookie

    async with SessionLocal() as s:
        user = await s.scalar(select(User))
        assert user.password_hash.startswith("$argon2id$")
        token_row = await s.scalar(select(RefreshToken))
        assert token_row.token_hash != client.cookies["refresh_token"]


async def test_signup_duplicate_email_is_case_insensitive(client):
    assert (await signup(client)).status_code == 201
    resp = await signup(client, email="ada@EXAMPLE.com")
    assert resp.status_code == 409


async def test_signup_rejects_short_password_and_bad_email(client):
    assert (await signup(client, password="short")).status_code == 422
    assert (await signup(client, email="not-an-email")).status_code == 422


async def test_failed_captcha_blocks_signup_and_login(client):
    resp = await signup(client, captcha=CAPTCHA_FAIL_TOKEN)
    assert resp.status_code == 400
    await signup(client)
    assert (await login(client, captcha=CAPTCHA_FAIL_TOKEN)).status_code == 400


async def test_login_and_me(client):
    await signup(client)
    resp = await login(client, email="ADA@example.com")
    assert resp.status_code == 200
    me = await client.get("/auth/me", headers=bearer(resp))
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"


async def test_login_errors_dont_reveal_whether_email_exists(client):
    await signup(client)
    wrong_pw = await login(client, password="wrong password")
    unknown = await login(client, email="nobody@example.com")
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()


async def test_me_requires_valid_token(client):
    assert (await client.get("/auth/me")).status_code == 401
    bad = await client.get("/auth/me", headers={"Authorization": "Bearer nonsense"})
    assert bad.status_code == 401


async def test_refresh_rotates_token(client):
    await signup(client)
    first = client.cookies["refresh_token"]
    resp = await client.post("/auth/refresh")
    assert resp.status_code == 200
    assert client.cookies["refresh_token"] != first
    assert (await client.get("/auth/me", headers=bearer(resp))).status_code == 200


async def test_reusing_a_rotated_refresh_token_revokes_the_family(client):
    await signup(client)
    stolen = client.cookies["refresh_token"]
    assert (await client.post("/auth/refresh")).status_code == 200
    current = client.cookies["refresh_token"]

    # Attacker replays the old token: rejected, and the cookie is cleared.
    client.cookies.set("refresh_token", stolen, path="/auth")
    replay = await client.post("/auth/refresh")
    assert replay.status_code == 401
    assert 'refresh_token=""' in replay.headers["set-cookie"]

    # The legitimate user's newer token was revoked too.
    client.cookies.set("refresh_token", current, path="/auth")
    assert (await client.post("/auth/refresh")).status_code == 401


async def test_refresh_without_cookie(client):
    assert (await client.post("/auth/refresh")).status_code == 401


async def test_logout_revokes_refresh_token(client):
    await signup(client)
    token = client.cookies["refresh_token"]
    assert (await client.post("/auth/logout")).status_code == 204
    client.cookies.set("refresh_token", token, path="/auth")
    assert (await client.post("/auth/refresh")).status_code == 401
