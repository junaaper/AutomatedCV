import uuid
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cv.models import CvChunk, CvDocument
from app.providers.embeddings import Embedder

# CV sections (a role, a project) are usually a few hundred characters; this keeps most
# intact while the overlap stops a bullet point being cut off from its context.
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800, chunk_overlap=100, separators=["\n\n", "\n", ". ", " ", ""]
)


@dataclass(frozen=True)
class Evidence:
    chunk_id: uuid.UUID
    content: str
    similarity: float


def chunk_text(text: str) -> list[str]:
    return [c.strip() for c in _splitter.split_text(text) if c.strip()]


async def ingest_cv(
    session: AsyncSession,
    user_id: uuid.UUID,
    text: str,
    filename: str | None,
    embedder: Embedder,
) -> tuple[CvDocument, int]:
    """Replaces the user's CV: chunk, embed, store. Embeds before touching the DB, so an
    embedding outage leaves the previous CV intact."""
    chunks = chunk_text(text)
    vectors = await embedder.embed_documents(chunks)

    await session.execute(delete(CvDocument).where(CvDocument.user_id == user_id))
    doc = CvDocument(user_id=user_id, filename=filename, content=text)
    session.add(doc)
    await session.flush()
    session.add_all(
        CvChunk(document_id=doc.id, user_id=user_id, chunk_index=i, content=c, embedding=v)
        for i, (c, v) in enumerate(zip(chunks, vectors, strict=True))
    )
    await session.commit()
    return doc, len(chunks)


async def search_cv(
    session: AsyncSession,
    user_id: uuid.UUID,
    queries: list[str],
    embedder: Embedder,
    k: int = 3,
) -> list[list[Evidence]]:
    """Top-k CV chunks for each query (one batched embedding call for all queries)."""
    if not queries:
        return []
    vectors = await embedder.embed_queries(queries)
    # Exact search over this user's chunks only. Every query is scoped to one CV (tens of
    # chunks), so exact KNN via the user_id index is both correct and fast. An approximate
    # HNSW scan would filter by user *after* collecting global candidates, and other users'
    # similar chunks could crowd out all of this user's results
    # (tests/test_retrieval_isolation.py). The MATERIALIZED CTE stops the planner from
    # answering the ORDER BY with a vector index.
    mine = (
        select(CvChunk.id, CvChunk.content, CvChunk.embedding)
        .where(CvChunk.user_id == user_id)
        .cte("mine")
        .prefix_with("MATERIALIZED")
    )
    results = []
    for vec in vectors:
        distance = mine.c.embedding.cosine_distance(vec).label("distance")
        rows = await session.execute(
            select(mine.c.id, mine.c.content, distance).order_by(distance).limit(k)
        )
        results.append([Evidence(r.id, r.content, round(1 - r.distance, 4)) for r in rows])
    return results


async def chunk_count(session: AsyncSession, doc_id: uuid.UUID) -> int:
    return await session.scalar(
        select(func.count()).select_from(CvChunk).where(CvChunk.document_id == doc_id)
    )
