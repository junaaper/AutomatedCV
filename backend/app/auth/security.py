import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from starlette.concurrency import run_in_threadpool

from app.config import get_settings

# argon2id with library defaults (OWASP-recommended parameters).
_hasher = PasswordHasher()
# Verified against when the email is unknown, so login timing doesn't reveal which emails exist.
_DUMMY_HASH = _hasher.hash("timing-equaliser")

JWT_ALGORITHM = "HS256"


async def hash_password(password: str) -> str:
    # argon2 is deliberately CPU/memory-heavy; keep it off the event loop.
    return await run_in_threadpool(_hasher.hash, password)


async def verify_password(password: str, password_hash: str | None) -> bool:
    """Pass password_hash=None for unknown users: still burns a full verify, always False."""

    def _verify() -> bool:
        try:
            _hasher.verify(password_hash or _DUMMY_HASH, password)
        except (VerifyMismatchError, InvalidHashError):
            return False
        return password_hash is not None

    return await run_in_threadpool(_verify)


def create_access_token(user_id: uuid.UUID, *, is_demo: bool = False) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "demo": is_demo,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID | None:
    """Returns the user id for a valid, unexpired access token, else None."""
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "type"]},
        )
    except jwt.PyJWTError:
        return None
    if payload["type"] != "access":
        return None
    try:
        return uuid.UUID(payload["sub"])
    except ValueError:
        return None


def new_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    # Refresh tokens are 256-bit random, so a fast hash is enough (no need for argon2).
    return hashlib.sha256(token.encode()).hexdigest()
