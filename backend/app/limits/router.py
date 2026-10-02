from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.auth.deps import CurrentUser
from app.db import SessionDep
from app.limits.quota import resets_at, usage_today, user_limit

router = APIRouter(tags=["limits"])


class Usage(BaseModel):
    used: int
    limit: int
    resets_at: datetime


@router.get("/usage")
async def usage(user: CurrentUser, session: SessionDep) -> Usage:
    """Today's live AI runs, for the usage meter in the UI."""
    return Usage(
        used=await usage_today(session, user), limit=user_limit(user), resets_at=resets_at()
    )
