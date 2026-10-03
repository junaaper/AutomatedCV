import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# Must equal settings.embed_dim; changing it needs a migration and a re-embed.
EMBED_DIM = 768


class CvDocument(Base):
    """A user's current CV. Uploading a new one replaces it (one per user)."""

    __tablename__ = "cv_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    filename: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CvChunk(Base):
    """One embedded passage of a CV.

    No vector index on purpose: every search is scoped to one user's few dozen chunks, so
    exact KNN through the user_id index beats an approximate global index, which would
    filter by user only after collecting candidates (see cv.service.search_cv).
    """

    __tablename__ = "cv_chunks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cv_documents.id", ondelete="CASCADE"), index=True
    )
    # Denormalised so retrieval filters by owner without a join.
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM))
