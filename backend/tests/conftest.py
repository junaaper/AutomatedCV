import asyncio
import os
import selectors
import sys

from dotenv import load_dotenv

# Must run before anything imports app.config / app.db.
# backend/.env may supply TEST_DATABASE_URL (e.g. a Neon test database); CI sets it directly.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/automatedcv_test",
)
os.environ.setdefault("LLM_PROVIDER", "fake")
os.environ.setdefault("EMBED_PROVIDER", "fake")

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


def pytest_asyncio_loop_factories(config, item):
    # psycopg async can't run on Windows' Proactor loop.
    if sys.platform == "win32":
        return {"selector": lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())}
    return {"default": asyncio.new_event_loop}


@pytest.fixture(scope="session")
def migrated_db():
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture
async def db(migrated_db):
    """Gives a test a migrated database and truncates all app tables afterwards."""
    yield
    tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    if tables:
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
