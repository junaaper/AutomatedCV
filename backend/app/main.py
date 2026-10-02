from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.auth.router import router as auth_router
from app.config import get_settings
from app.cv.router import router as cv_router
from app.db import SessionDep


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AutomatedCV API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(cv_router)

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
