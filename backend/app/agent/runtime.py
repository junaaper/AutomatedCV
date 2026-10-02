"""Owns the compiled graph and its Postgres checkpointer connection pool.

Created lazily on first use (and eagerly at app startup), closed at shutdown. Checkpoints
live in Postgres, so a run paused for review survives Render putting the service to sleep.
"""

import asyncio

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.agent.graph import build_graph
from app.config import get_settings

_lock = asyncio.Lock()
_pool: AsyncConnectionPool | None = None
_graph: CompiledStateGraph | None = None


def _libpq_url(sqlalchemy_url: str) -> str:
    return sqlalchemy_url.replace("postgresql+psycopg://", "postgresql://", 1)


async def get_graph() -> CompiledStateGraph:
    global _pool, _graph
    if _graph is not None:
        return _graph
    async with _lock:
        if _graph is None:
            pool = AsyncConnectionPool(
                _libpq_url(get_settings().database_url),
                min_size=1,
                max_size=5,
                open=False,
                # prepare_threshold=0: Neon's pooled endpoint (PgBouncer) can't keep
                # server-side prepared statements across transactions.
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                    "row_factory": dict_row,
                    "connect_timeout": 15,
                },
                # Neon scales to zero; drop dead connections instead of failing a request.
                check=AsyncConnectionPool.check_connection,
            )
            await pool.open()
            saver = AsyncPostgresSaver(pool)
            await saver.setup()  # idempotent; creates/migrates LangGraph's own tables
            _pool, _graph = pool, build_graph().compile(checkpointer=saver)
    return _graph


async def close_graph() -> None:
    global _pool, _graph
    async with _lock:
        if _pool is not None:
            await _pool.close()
        _pool, _graph = None, None
