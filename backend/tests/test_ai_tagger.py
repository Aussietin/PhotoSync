"""
Unit tests for services/ai_tagger.py.

The OpenAI backend is tested with a mocked httpx response so no real API
call is made and no key is required. Heuristic and error-fallback paths are
tested with a real (tiny) in-memory JPEG.
"""
import json
import io
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import Base
from models.photo import Photo, Tag


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def tiny_jpeg(tmp_path) -> Path:
    """Write a tiny 8×8 bright-warm JPEG to tmp_path and return its path.

    Color (240, 180, 180): r > g ≈ b → "warm tones"; mean ≈ 200 > 180 → "bright".
    """
    from PIL import Image
    img = Image.new("RGB", (8, 8), color=(240, 180, 180))
    p = tmp_path / "test.jpg"
    img.save(p, format="JPEG")
    return p


@pytest_asyncio.fixture
async def photo_row(session, tiny_jpeg) -> Photo:
    p = Photo(
        filename="test.jpg",
        original_filename="test.jpg",
        file_path=str(tiny_jpeg),
        thumbnail_path=str(tiny_jpeg),
        file_size=512,
        mime_type="image/jpeg",
    )
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


# ── Heuristic tagger ──────────────────────────────────────────────────────────

async def test_heuristic_tags_warm_bright(session, photo_row):
    """A bright red image should get warm tones + bright tags."""
    from services.ai_tagger import tag_photo

    with patch("config.settings.OPENAI_API_KEY", ""):
        tags = await tag_photo(session, photo_row)

    assert "warm tones" in tags
    assert "bright" in tags


async def test_heuristic_tags_persisted_to_db(session, photo_row):
    """Tags written by heuristic path are stored on the Photo row and as Tag rows."""
    from services.ai_tagger import tag_photo
    from sqlalchemy import select

    with patch("config.settings.OPENAI_API_KEY", ""):
        tags = await tag_photo(session, photo_row)

    assert tags  # heuristic always returns at least one tag
    assert photo_row.ai_tags == json.dumps(tags)

    db_tags = (await session.execute(
        select(Tag).where(Tag.photo_id == photo_row.id, Tag.source == "ai")
    )).scalars().all()
    assert {t.name for t in db_tags} == set(tags)


async def test_heuristic_skips_missing_file(session):
    """A photo whose file no longer exists returns an empty list without error."""
    from services.ai_tagger import tag_photo

    p = Photo(
        filename="gone.jpg",
        original_filename="gone.jpg",
        file_path="/nonexistent/path/gone.jpg",
        file_size=0,
        mime_type="image/jpeg",
    )
    session.add(p)
    await session.commit()
    await session.refresh(p)

    with patch("config.settings.OPENAI_API_KEY", ""):
        tags = await tag_photo(session, p)

    assert tags == []


# ── OpenAI backend ────────────────────────────────────────────────────────────

def _mock_openai_response(tags: list[str], description: str):
    """Build a fake httpx Response-like object for the OpenAI chat completions endpoint."""
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"tags": tags, "description": description})
                }
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=payload)
    return mock_resp


async def test_openai_tags_and_description(session, photo_row):
    """When OPENAI_API_KEY is set the OpenAI path is used and description is stored."""
    from services.ai_tagger import tag_photo

    expected_tags = ["sunset", "beach", "golden hour", "warm colours", "seascape"]
    expected_desc = "A warm sunset over a calm beach."

    mock_resp = _mock_openai_response(expected_tags, expected_desc)

    with (
        patch("config.settings.OPENAI_API_KEY", "sk-test"),
        patch("httpx.AsyncClient") as MockClient,
    ):
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.post = AsyncMock(return_value=mock_resp)
        MockClient.return_value = instance

        tags = await tag_photo(session, photo_row)

    assert tags == expected_tags
    assert photo_row.ai_tags == json.dumps(expected_tags)
    assert photo_row.ai_description == expected_desc


async def test_openai_fallback_on_error(session, photo_row):
    """If the OpenAI call raises an exception, the heuristic is NOT run either —
    tag_photo returns [] gracefully (the caller decides what to do next)."""
    from services.ai_tagger import tag_photo

    with (
        patch("config.settings.OPENAI_API_KEY", "sk-test"),
        patch("httpx.AsyncClient") as MockClient,
    ):
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.post = AsyncMock(side_effect=Exception("network error"))
        MockClient.return_value = instance

        tags = await tag_photo(session, photo_row)

    # OpenAI failed → _tag_with_openai returns ([], None) → tag_photo returns []
    assert tags == []


async def test_openai_replaces_existing_ai_tags(session, photo_row):
    """Re-tagging a photo removes old AI Tag rows and sets fresh ones."""
    from services.ai_tagger import tag_photo
    from sqlalchemy import select

    # Seed an old AI tag directly.
    session.add(Tag(photo_id=photo_row.id, name="old tag", source="ai", confidence=0.5))
    await session.commit()

    first_tags = ["sunset", "warm colours"]
    mock_resp = _mock_openai_response(first_tags, "New description.")

    with (
        patch("config.settings.OPENAI_API_KEY", "sk-test"),
        patch("httpx.AsyncClient") as MockClient,
    ):
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.post = AsyncMock(return_value=mock_resp)
        MockClient.return_value = instance

        tags = await tag_photo(session, photo_row)

    db_tags = (await session.execute(
        select(Tag).where(Tag.photo_id == photo_row.id, Tag.source == "ai")
    )).scalars().all()
    tag_names = {t.name for t in db_tags}
    assert "old tag" not in tag_names
    assert tag_names == set(first_tags)
