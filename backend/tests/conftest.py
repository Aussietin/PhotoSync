"""
Shared pytest fixtures for PhotoSync integration tests.

Uses an in-memory SQLite DB so tests are isolated and fast.
The lifespan's init_db() and reap_stale_jobs() are patched to no-ops so we
don't hit the real on-disk DB or stale-job cleanup on every test.
"""
import os
import sys
from unittest.mock import patch, AsyncMock
from pathlib import Path

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from database import Base, get_db
from config import settings

# The FastAPI app mounts static-file dirs at import time — they must exist.
# Create them now (they're git-ignored); tests never write real files here.
for _d in (settings.UPLOAD_DIR, settings.THUMBNAIL_DIR, settings.PREVIEW_DIR):
    os.makedirs(_d, exist_ok=True)


@pytest_asyncio.fixture
async def db_engine():
    # StaticPool reuses a single connection so all sessions see the same in-memory DB.
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """A raw AsyncSession for seeding test data directly."""
    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    """AsyncClient wired to the FastAPI app with an isolated in-memory DB."""
    import app as app_module

    Session = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override_db():
        async with Session() as s:
            yield s

    app_module.app.dependency_overrides[get_db] = _override_db

    with (
        patch("app.init_db", new_callable=AsyncMock),
        patch("services.jobs.reap_stale_jobs", new_callable=AsyncMock),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_module.app), base_url="http://test"
        ) as c:
            yield c

    app_module.app.dependency_overrides.clear()
