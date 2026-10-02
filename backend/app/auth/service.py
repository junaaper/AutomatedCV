import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken, User
from app.auth.security import hash_refresh_token, new_refresh_token
from app.config import get_settings


class InvalidRefreshToken(Exception):
    pass


async def issue_refresh_token(
    session: AsyncSession, user_id: uuid.UUID, family_id: uuid.UUID | None = None
) -> str:
    """Stores a new refresh token (hashed) and returns the plaintext for the cookie."""
    token = new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user_id,
            family_id=family_id or uuid.uuid4(),
            token_hash=hash_refresh_token(token),
            expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days),
        )
    )
    await session.flush()
    return token


async def rotate_refresh_token(session: AsyncSession, token: str) -> tuple[User, str]:
    """Swaps a valid refresh token for a new one in the same family.

    Presenting an already-revoked token means it was copied, so we revoke the whole
    family, which logs out both the attacker and the real user.
    """
    row = await session.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(token))
        .with_for_update()
    )
    now = datetime.now(UTC)
    if row is None:
        raise InvalidRefreshToken
    if row.revoked_at is not None:
        await _revoke_family(session, row.family_id, now)
        await session.commit()
        raise InvalidRefreshToken
    if row.expires_at <= now:
        raise InvalidRefreshToken

    row.revoked_at = now
    user = await session.get_one(User, row.user_id)
    new_token = await issue_refresh_token(session, user.id, row.family_id)
    return user, new_token


async def revoke_refresh_token(session: AsyncSession, token: str) -> None:
    row = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(token))
    )
    if row is not None:
        await _revoke_family(session, row.family_id, datetime.now(UTC))


async def _revoke_family(session: AsyncSession, family_id: uuid.UUID, now: datetime) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
