import logging
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.auth.deps import CurrentUser
from app.cv.extract import MAX_PDF_BYTES, CvExtractionError, extract_pdf_text, validate_cv_text
from app.cv.models import CvDocument
from app.cv.service import chunk_count, ingest_cv, search_cv
from app.db import SessionDep
from app.demo.service import embedder_for
from app.providers.embeddings import Embedder, get_embedder

log = logging.getLogger(__name__)
router = APIRouter(prefix="/cv", tags=["cv"])

EmbedderDep = Annotated[Embedder, Depends(get_embedder)]


class CvOut(BaseModel):
    id: uuid.UUID
    filename: str | None
    content: str
    chunk_count: int
    created_at: datetime


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    k: int = Field(default=3, ge=1, le=10)


class EvidenceOut(BaseModel):
    chunk_id: uuid.UUID
    content: str
    similarity: float


def _embedding_unavailable(exc: Exception) -> HTTPException:
    log.exception("Embedding provider failed", exc_info=exc)
    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE, "The embedding service is unavailable; try again."
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_cv(
    user: CurrentUser,
    session: SessionDep,
    embedder: EmbedderDep,
    file: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form()] = None,
) -> CvOut:
    """Upload a CV as a PDF file or as pasted text (exactly one). Replaces any existing CV."""
    if (file is None) == (text is None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Send either a PDF or text.")
    try:
        if file is not None:
            data = await file.read(MAX_PDF_BYTES + 1)
            if len(data) > MAX_PDF_BYTES:
                raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "PDF must be under 5 MB.")
            if not data.startswith(b"%PDF"):
                raise CvExtractionError("Only PDF files are supported.")
            content, filename = extract_pdf_text(data), file.filename
        else:
            content, filename = validate_cv_text(text), None
    except CvExtractionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None

    try:
        doc, n_chunks = await ingest_cv(
            session, user.id, content, filename, embedder_for(user, embedder)
        )
    except Exception as exc:  # any provider/network failure
        raise _embedding_unavailable(exc) from None
    return CvOut(
        id=doc.id,
        filename=doc.filename,
        content=doc.content,
        chunk_count=n_chunks,
        created_at=doc.created_at,
    )


@router.get("")
async def get_cv(user: CurrentUser, session: SessionDep) -> CvOut:
    doc = await session.scalar(select(CvDocument).where(CvDocument.user_id == user.id))
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No CV uploaded yet")
    return CvOut(
        id=doc.id,
        filename=doc.filename,
        content=doc.content,
        chunk_count=await chunk_count(session, doc.id),
        created_at=doc.created_at,
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cv(user: CurrentUser, session: SessionDep) -> None:
    await session.execute(delete(CvDocument).where(CvDocument.user_id == user.id))
    await session.commit()


@router.post("/search")
async def search(
    body: SearchRequest, user: CurrentUser, session: SessionDep, embedder: EmbedderDep
) -> list[EvidenceOut]:
    """Debug/insight endpoint: which parts of my CV match this phrase?"""
    try:
        [hits] = await search_cv(
            session, user.id, [body.query], embedder_for(user, embedder), k=body.k
        )
    except Exception as exc:
        raise _embedding_unavailable(exc) from None
    return [
        EvidenceOut(chunk_id=h.chunk_id, content=h.content, similarity=h.similarity) for h in hits
    ]
