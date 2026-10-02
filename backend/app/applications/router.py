import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.applications.models import Application, ApplicationStatus
from app.auth.deps import CurrentUser
from app.db import SessionDep

router = APIRouter(prefix="/applications", tags=["tracker"])


class ApplicationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID | None
    title: str
    company: str
    fit_score: int
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime


class ApplicationDetail(ApplicationSummary):
    posting: str
    requirements: dict[str, Any]
    fit: dict[str, Any]
    cover_letter: str
    notes: str | None


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = Field(default=None, max_length=5_000)
    cover_letter: str | None = Field(default=None, min_length=1, max_length=10_000)


async def _owned(session, app_id: uuid.UUID, user_id: uuid.UUID) -> Application:
    app = await session.get(Application, app_id)
    if app is None or app.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return app


@router.get("")
async def list_applications(user: CurrentUser, session: SessionDep) -> list[ApplicationSummary]:
    apps = await session.scalars(
        select(Application)
        .where(Application.user_id == user.id)
        .order_by(Application.created_at.desc())
    )
    return [ApplicationSummary.model_validate(a) for a in apps]


@router.get("/{app_id}")
async def get_application(
    app_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> ApplicationDetail:
    return ApplicationDetail.model_validate(await _owned(session, app_id, user.id))


@router.patch("/{app_id}")
async def update_application(
    app_id: uuid.UUID, body: ApplicationUpdate, user: CurrentUser, session: SessionDep
) -> ApplicationDetail:
    app = await _owned(session, app_id, user.id)
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(app, field, value)
    await session.commit()
    await session.refresh(app)
    return ApplicationDetail.model_validate(app)


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(app_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    await session.delete(await _owned(session, app_id, user.id))
    await session.commit()
