import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class LlmUsage(Base):
    """Live LLM-backed agent runs per user per UTC day."""

    __tablename__ = "llm_usage"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    runs: Mapped[int] = mapped_column(Integer, default=0)
