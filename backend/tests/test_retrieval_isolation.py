import uuid

import pytest
from sqlalchemy import text

from app.auth.models import User
from app.cv.models import EMBED_DIM, CvChunk, CvDocument
from app.cv.service import search_cv
from app.db import SessionLocal
from app.providers.embeddings import HashingEmbedder

pytestmark = pytest.mark.usefixtures("db")


async def _user_with_chunks(session, texts: list[str], embedder) -> uuid.UUID:
    user = User(email=f"{uuid.uuid4().hex}@example.com", password_hash="x")
    session.add(user)
    await session.flush()
    doc = CvDocument(user_id=user.id, content="\n".join(texts))
    session.add(doc)
    await session.flush()
    vectors = await embedder.embed_documents(texts)
    session.add_all(
        CvChunk(document_id=doc.id, user_id=user.id, chunk_index=i, content=t, embedding=v)
        for i, (t, v) in enumerate(zip(texts, vectors, strict=True))
    )
    await session.commit()
    return user.id


async def test_filtered_vector_search_returns_k_results_despite_crowding():
    """Another user's near-identical chunks must not starve this user's results.

    An HNSW index scan collects the globally nearest candidates and only then applies the
    user filter; without iterative scans, a crowded index can return fewer than k rows.
    """
    embedder = HashingEmbedder(EMBED_DIM)
    async with SessionLocal() as s:
        crowd = [f"Built REST APIs in Python with FastAPI, variant {i}" for i in range(400)]
        await _user_with_chunks(s, crowd, embedder)
        mine = await _user_with_chunks(
            s,
            [
                "Designed PostgreSQL schemas and tuned queries.",
                "Shipped React dashboards in TypeScript.",
                "Mentored two junior engineers.",
            ],
            embedder,
        )
        await s.execute(text("ANALYZE cv_chunks"))
        await s.commit()

        # Worst case for the planner, inside a transaction that's rolled back: no user_id
        # index and sequential scans discouraged. If an HNSW index existed (as in an
        # earlier schema), this is where it would be chosen and return 0 rows.
        await s.execute(text("DROP INDEX ix_cv_chunks_user_id"))
        await s.execute(text("SET LOCAL enable_seqscan = off"))
        [hits] = await search_cv(s, mine, ["Python FastAPI REST APIs"], embedder, k=3)
        await s.rollback()
    assert len(hits) == 3
    assert {h.content for h in hits} == {
        "Designed PostgreSQL schemas and tuned queries.",
        "Shipped React dashboards in TypeScript.",
        "Mentored two junior engineers.",
    }


async def test_no_vector_index_is_used_for_scoped_search():
    async with SessionLocal() as s:
        indexes = (
            await s.execute(text("SELECT indexdef FROM pg_indexes WHERE tablename = 'cv_chunks'"))
        ).scalars()
        assert not any("hnsw" in i.lower() or "ivfflat" in i.lower() for i in indexes)
