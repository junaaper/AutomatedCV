import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.agent.router import router as agent_router
from app.agent.runtime import close_graph, get_graph
from app.applications.router import router as applications_router
from app.auth.router import router as auth_router
from app.config import get_settings
from app.cv.router import router as cv_router
from app.db import SessionDep, SessionLocal
from app.demo.router import router as demo_router
from app.demo.service import purge_expired_demo_users

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        graph = await get_graph()  # open the checkpointer pool and set up its tables at boot
        async with SessionLocal() as session:
            await purge_expired_demo_users(session, graph.checkpointer)
    except Exception:
        # Don't block startup (healthz must answer during cold starts); the graph is
        # created lazily on first use instead.
        log.exception("Startup warm-up failed")
    yield
    await close_graph()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AutomatedCV API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(cv_router)
    app.include_router(agent_router)
    app.include_router(applications_router)
    app.include_router(demo_router)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        # Deliberately DB-free: the frontend polls this while Render wakes the service.
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz(session: SessionDep) -> dict[str, str]:
        await session.execute(text("SELECT 1"))
        return {"status": "ready"}

    return app


app = create_app()
