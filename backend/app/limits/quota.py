"""Daily quotas on live LLM usage. Protects the free API key (a global cap) and keeps
one user from using it all (a per-user cap). Replayed demo runs don't count."""

from datetime import UTC, date, datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.config import get_settings
from app.limits.models import LlmUsage


def today() -> date:
    return datetime.now(UTC).date()


def resets_at() -> datetime:
    return datetime.combine(today() + timedelta(days=1), time.min, tzinfo=UTC)


def user_limit(user: User) -> int:
    s = get_settings()
    return s.demo_daily_llm_runs if user.is_demo else s.daily_llm_runs_per_user


def _exceeded(message: str) -> HTTPException:
    seconds = int((resets_at() - datetime.now(UTC)).total_seconds())
    return HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS, message, headers={"Retry-After": str(seconds)}
    )


async def consume_llm_run(session: AsyncSession, user: User) -> int:
    """Atomically counts one live run against today's quotas; raises 429 when exhausted.

    The conditional upsert means concurrent requests can't push a user past the limit.
    """
    settings = get_settings()
    total = await session.scalar(
        select(func.coalesce(func.sum(LlmUsage.runs), 0)).where(LlmUsage.day == today())
    )
    if total >= settings.global_daily_llm_runs:
        raise _exceeded(
            "The demo's shared AI budget for today is used up. It resets at midnight UTC; "
            "sample postings in the demo still work."
        )

    limit = user_limit(user)
    stmt = (
        insert(LlmUsage)
        .values(user_id=user.id, day=today(), runs=1)
        .on_conflict_do_update(
            index_elements=[LlmUsage.user_id, LlmUsage.day],
            set_={"runs": LlmUsage.runs + 1},
            where=LlmUsage.runs < limit,
        )
        .returning(LlmUsage.runs)
    )
    used = await session.scalar(stmt) if limit > 0 else None
    await session.commit()
    if used is None:
        raise _exceeded(f"You've used today's {limit} AI runs. The limit resets at midnight UTC.")
    return used


async def usage_today(session: AsyncSession, user: User) -> int:
    return (
        await session.scalar(
            select(LlmUsage.runs).where(LlmUsage.user_id == user.id, LlmUsage.day == today())
        )
        or 0
    )
