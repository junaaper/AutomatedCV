from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.providers.embeddings import Embedder


class AgentState(TypedDict, total=False):
    """Checkpointed graph state. Plain JSON-able dicts, so checkpoints stay readable and
    don't depend on pickling our classes."""

    user_id: str
    run_id: str
    posting: str
    job: dict[str, Any]  # JobRequirements
    evidence: dict[str, list[dict[str, Any]]]  # requirement -> retrieved CV chunks
    fit: dict[str, Any]  # FitResult
    cover_letter: str
    feedback: str | None
    revisions: int
    decision: Literal["approve", "edit", "reject"] | None
    application_id: str | None


@dataclass(frozen=True)
class AgentContext:
    """Per-invocation dependencies (not checkpointed), injected via LangGraph's Runtime."""

    llm: BaseChatModel
    embedder: Embedder
    session_factory: async_sessionmaker[AsyncSession]
    max_revisions: int = 3


class AgentError(RuntimeError):
    """A failure we can explain to the user (shown verbatim in the UI)."""
