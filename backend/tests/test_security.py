import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.auth import security
from app.config import get_settings


async def test_password_hash_is_argon2id_and_verifies():
    h = await security.hash_password("correct horse battery")
    assert h.startswith("$argon2id$")
    assert "correct horse" not in h
    assert await security.verify_password("correct horse battery", h)
    assert not await security.verify_password("wrong password", h)


async def test_verify_with_no_hash_is_always_false():
    assert not await security.verify_password("timing-equaliser", None)


def test_access_token_roundtrip():
    uid = uuid.uuid4()
    assert security.decode_access_token(security.create_access_token(uid)) == uid


def test_expired_token_rejected():
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "access", "iat": now, "exp": now - timedelta(seconds=1)},
        get_settings().jwt_secret,
        algorithm=security.JWT_ALGORITHM,
    )
    assert security.decode_access_token(token) is None


def test_token_signed_with_other_secret_rejected():
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "access", "exp": datetime.now(UTC) + timedelta(hours=1)},
        "attacker-secret-that-is-long-enough-for-hs256",
        algorithm=security.JWT_ALGORITHM,
    )
    assert security.decode_access_token(token) is None


def test_alg_none_rejected():
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "access", "exp": datetime.now(UTC) + timedelta(hours=1)},
        None,
        algorithm="none",
    )
    assert security.decode_access_token(token) is None


def test_refresh_token_hash_is_stable_and_not_the_token():
    t = security.new_refresh_token()
    assert security.hash_refresh_token(t) == security.hash_refresh_token(t)
    assert security.hash_refresh_token(t) != t
