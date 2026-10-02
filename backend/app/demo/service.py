import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.models import AgentRun, Application, ApplicationStatus
from app.auth.models import User
from app.cv.models import EMBED_DIM
from app.cv.service import ingest_cv
from app.demo.content import DEMO_CV, SAMPLE_POSTINGS, normalise_posting
from app.demo.replay import ReplayChatModel
from app.providers.embeddings import Embedder, HashingEmbedder

log = logging.getLogger(__name__)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
DEMO_TTL = timedelta(hours=24)
DEMO_EMAIL_DOMAIN = "demo.automatedcv.local"

# Pre-filled tracker entries so the demo account looks lived-in.
SEEDED = [
    (
        "frontend-product",
        ApplicationStatus.interviewing,
        "Intro call went well; take-home due Friday.",
    ),
    ("ml-platform", ApplicationStatus.applied, "Stretch role: Kubernetes and PyTorch are gaps."),
]


@lru_cache
def load_fixtures() -> dict[str, dict[str, Any]]:
    fixtures = {}
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        fixtures[data["id"]] = data
    return fixtures


def fixture_for_posting(posting: str) -> dict[str, Any] | None:
    norm = normalise_posting(posting)
    for sample in SAMPLE_POSTINGS:
        if normalise_posting(sample.posting) == norm:
            return load_fixtures().get(sample.id)
    return None


def demo_embedder() -> Embedder:
    # Demo users always use the offline embedder: no API dependency, and identical
    # retrieval to when the fixtures were recorded, so replayed quotes stay grounded.
    return HashingEmbedder(EMBED_DIM)


def embedder_for(user: User, default: Embedder) -> Embedder:
    return demo_embedder() if user.is_demo else default


def llm_for(user: User, posting: str, live: BaseChatModel) -> BaseChatModel:
    """Demo runs on a sample posting replay recorded responses (falling back to the live
    model for anything unrecorded, like free-text revision feedback)."""
    if user.is_demo and (fixture := fixture_for_posting(posting)):
        return ReplayChatModel(responses=fixture["responses"], fallback=live)
    return live


async def create_demo_user(session: AsyncSession) -> User:
    user = User(
        email=f"demo-{uuid.uuid4().hex[:10]}@{DEMO_EMAIL_DOMAIN}",
        password_hash="!demo",  # not a valid argon2 hash, so password login is impossible
        is_demo=True,
    )
    session.add(user)
    await session.flush()
    await ingest_cv(session, user.id, DEMO_CV, "sam-rivera-cv.pdf", demo_embedder())

    fixtures = load_fixtures()
    samples = {s.id: s for s in SAMPLE_POSTINGS}
    for sample_id, status, notes in SEEDED:
        if (fx := fixtures.get(sample_id)) is None:
            continue
        snap = fx["snapshot"]
        session.add(
            Application(
                user_id=user.id,
                title=snap["job"]["title"],
                company=snap["job"]["company"],
                posting=samples[sample_id].posting,
                requirements=snap["job"],
                fit=snap["fit"],
                fit_score=snap["fit"]["score"],
                cover_letter=snap["cover_letter"],
                status=status,
                notes=notes,
            )
        )
    await session.commit()
    return user


async def purge_expired_demo_users(session: AsyncSession, checkpointer: Any | None = None) -> int:
    cutoff = datetime.now(UTC) - DEMO_TTL
    expired = (
        await session.scalars(select(User.id).where(User.is_demo, User.created_at < cutoff))
    ).all()
    if not expired:
        return 0
    if checkpointer is not None:
        run_ids = (
            await session.scalars(select(AgentRun.id).where(AgentRun.user_id.in_(expired)))
        ).all()
        for run_id in run_ids:
            await checkpointer.adelete_thread(str(run_id))
    await session.execute(delete(User).where(User.id.in_(expired)))  # cascades
    await session.commit()
    log.info("Purged %d expired demo users", len(expired))
    return len(expired)
