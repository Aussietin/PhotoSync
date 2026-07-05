"""
Unit tests for services/ai_tagger.py and services/embeddings.py.

The local CLIP model is never loaded here — its image/text encoders are mocked,
so no torch/sentence-transformers install or model download is needed. This
covers both the CLIP path (mocked vectors) and the colour-heuristic fallback
that runs when the model is unavailable.
"""
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest_asyncio
from sqlalchemy import select
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
    """A tiny bright-warm JPEG: r > g ≈ b → 'warm tones'; mean ≈ 200 → 'bright'."""
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


# ── Heuristic fallback (CLIP model unavailable) ─────────────────────────────────

async def test_heuristic_tags_warm_bright(session, photo_row):
    """With no CLIP model, a bright warm image gets warm tones + bright tags."""
    from services.ai_tagger import tag_photo

    with patch("services.embeddings.embed_image", return_value=None):
        tags = await tag_photo(session, photo_row)

    assert "warm tones" in tags
    assert "bright" in tags
    assert photo_row.clip_embedding is None  # no embedding without the model


async def test_heuristic_tags_persisted_to_db(session, photo_row):
    """Heuristic tags are stored on the Photo row and as Tag rows."""
    from services.ai_tagger import tag_photo

    with patch("services.embeddings.embed_image", return_value=None):
        tags = await tag_photo(session, photo_row)

    assert tags
    assert photo_row.ai_tags == json.dumps(tags)
    db_tags = (await session.execute(
        select(Tag).where(Tag.photo_id == photo_row.id, Tag.source == "ai")
    )).scalars().all()
    assert {t.name for t in db_tags} == set(tags)


async def test_skips_missing_file(session):
    """A photo whose file no longer exists returns [] without error."""
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

    tags = await tag_photo(session, p)
    assert tags == []


# ── CLIP path (mocked encoder) ──────────────────────────────────────────────────

async def test_clip_tags_and_embedding_persisted(session, photo_row):
    """When the model is available, tag_photo stores zero-shot tags + embedding."""
    from services.ai_tagger import tag_photo

    fake_vec = np.ones(512, dtype=np.float32)
    expected = ["beach", "sunset", "dog"]

    with (
        patch("services.embeddings.embed_image", return_value=fake_vec),
        patch("services.embeddings.zero_shot_tags", return_value=expected),
    ):
        tags = await tag_photo(session, photo_row)

    assert tags == expected
    assert photo_row.ai_tags == json.dumps(expected)
    # Embedding stored and round-trips back to the same vector.
    assert photo_row.clip_embedding is not None
    from services import embeddings
    np.testing.assert_array_equal(embeddings.from_blob(photo_row.clip_embedding), fake_vec)


async def test_clip_replaces_existing_ai_tags(session, photo_row):
    """Re-tagging removes old AI Tag rows and writes fresh ones."""
    from services.ai_tagger import tag_photo

    session.add(Tag(photo_id=photo_row.id, name="old tag", source="ai", confidence=0.5))
    await session.commit()

    fake_vec = np.ones(512, dtype=np.float32)
    new_tags = ["food", "indoors"]

    with (
        patch("services.embeddings.embed_image", return_value=fake_vec),
        patch("services.embeddings.zero_shot_tags", return_value=new_tags),
    ):
        await tag_photo(session, photo_row)

    db_tags = (await session.execute(
        select(Tag).where(Tag.photo_id == photo_row.id, Tag.source == "ai")
    )).scalars().all()
    names = {t.name for t in db_tags}
    assert "old tag" not in names
    assert names == set(new_tags)


# ── Batch tagging (bulk analyze pass) ───────────────────────────────────────────

@pytest_asyncio.fixture
async def photo_rows(session, tmp_path) -> list[Photo]:
    from PIL import Image

    rows = []
    for i in range(3):
        img_path = tmp_path / f"test{i}.jpg"
        Image.new("RGB", (8, 8), color=(240, 180, 180)).save(img_path, format="JPEG")
        p = Photo(
            filename=f"test{i}.jpg",
            original_filename=f"test{i}.jpg",
            file_path=str(img_path),
            thumbnail_path=str(img_path),
            file_size=512,
            mime_type="image/jpeg",
        )
        session.add(p)
        rows.append(p)
    await session.commit()
    for p in rows:
        await session.refresh(p)
    return rows


async def test_batch_heuristic_tags_all_photos(session, photo_rows):
    """With no CLIP model, tag_photos_batch falls back to heuristics for each photo."""
    from services.ai_tagger import tag_photos_batch

    with patch("services.embeddings.embed_images", return_value=[None] * len(photo_rows)):
        count = await tag_photos_batch(session, photo_rows)

    assert count == len(photo_rows)
    for p in photo_rows:
        assert p.ai_tags
        assert p.clip_embedding is None


async def test_batch_clip_tags_and_embeddings_persisted(session, photo_rows):
    """One mocked batch embed call tags + embeds every photo in the batch."""
    from services.ai_tagger import tag_photos_batch

    fake_vecs = [np.ones(512, dtype=np.float32) for _ in photo_rows]
    expected = ["beach", "sunset"]

    with (
        patch("services.embeddings.embed_images", return_value=fake_vecs) as mock_embed,
        patch("services.embeddings.zero_shot_tags", return_value=expected),
    ):
        count = await tag_photos_batch(session, photo_rows)

    mock_embed.assert_called_once()  # one batch call, not one per photo
    assert count == len(photo_rows)
    for p in photo_rows:
        assert p.ai_tags == json.dumps(expected)
        assert p.clip_embedding is not None


async def test_batch_skips_photos_with_missing_files(session, photo_rows):
    """A photo with no resolvable file is excluded from the batch and the count."""
    from services.ai_tagger import tag_photos_batch

    gone = Photo(
        filename="gone.jpg", original_filename="gone.jpg",
        file_path="/nonexistent/gone.jpg", file_size=0, mime_type="image/jpeg",
    )
    session.add(gone)
    await session.commit()
    await session.refresh(gone)

    with patch("services.embeddings.embed_images", return_value=[None] * len(photo_rows)) as mock_embed:
        count = await tag_photos_batch(session, photo_rows + [gone])

    assert count == len(photo_rows)
    assert gone.ai_tags is None
    # Only the resolvable photos' paths were passed to the batch embedder.
    assert len(mock_embed.call_args[0][0]) == len(photo_rows)


# ── embed_images (real batching, model mocked) ──────────────────────────────────

def test_embed_images_batches_into_one_encode_call(tiny_jpeg):
    """embed_images opens every image but calls model.encode exactly once."""
    from services import embeddings

    fake_model = type("FakeModel", (), {
        "encode": lambda self, imgs, **kw: np.stack([np.ones(4, dtype=np.float32)] * len(imgs)),
    })()

    with patch("services.embeddings._get_model", return_value=fake_model):
        vecs = embeddings.embed_images([tiny_jpeg, tiny_jpeg])

    assert len(vecs) == 2
    assert all(v is not None for v in vecs)


def test_embed_images_returns_none_list_when_model_unavailable(tiny_jpeg):
    from services import embeddings

    with patch("services.embeddings._get_model", return_value=None):
        vecs = embeddings.embed_images([tiny_jpeg, tiny_jpeg])

    assert vecs == [None, None]


def test_embed_images_marks_unopenable_paths_as_none(tiny_jpeg):
    """A bad path among good ones doesn't fail the whole batch — it's just None."""
    from services import embeddings

    fake_model = type("FakeModel", (), {
        "encode": lambda self, imgs, **kw: np.stack([np.ones(4, dtype=np.float32)] * len(imgs)),
    })()

    with patch("services.embeddings._get_model", return_value=fake_model):
        vecs = embeddings.embed_images([tiny_jpeg, Path("/nonexistent/bad.jpg")])

    assert vecs[0] is not None
    assert vecs[1] is None


# ── Embedding helpers ───────────────────────────────────────────────────────────

def test_blob_roundtrip():
    from services import embeddings
    vec = np.array([0.1, -0.2, 0.3, 0.4], dtype=np.float32)
    out = embeddings.from_blob(embeddings.to_blob(vec))
    np.testing.assert_array_equal(out, vec)


def test_rank_by_similarity_orders_by_cosine():
    """rank_by_similarity returns dot products aligned with the input order."""
    from services import embeddings

    query = np.array([1.0, 0.0], dtype=np.float32)
    blobs = [
        embeddings.to_blob(np.array([1.0, 0.0], dtype=np.float32)),   # identical -> 1.0
        embeddings.to_blob(np.array([0.0, 1.0], dtype=np.float32)),   # orthogonal -> 0.0
        embeddings.to_blob(np.array([-1.0, 0.0], dtype=np.float32)),  # opposite -> -1.0
    ]
    scores = embeddings.rank_by_similarity(query, blobs)
    assert list(np.round(scores, 3)) == [1.0, 0.0, -1.0]


def test_rank_by_similarity_empty():
    from services import embeddings
    scores = embeddings.rank_by_similarity(np.ones(4, dtype=np.float32), [])
    assert len(scores) == 0


def test_zero_shot_tags_thresholds_and_orders():
    """zero_shot_tags keeps labels above threshold, best-first, capped at max."""
    from services import embeddings

    labels = ["a dog", "a cat", "a beach"]
    # label matrix: dog highly aligned, cat moderate, beach negative
    label_mat = np.array([
        [1.0, 0.0],   # dog
        [0.5, 0.0],   # cat
        [-1.0, 0.0],  # beach
    ], dtype=np.float32)
    img_vec = np.array([1.0, 0.0], dtype=np.float32)

    with patch("services.embeddings._label_embeddings",
               return_value=(["dog", "cat", "beach"], label_mat)):
        tags = embeddings.zero_shot_tags(img_vec, labels=labels, threshold=0.3, max_tags=5)

    assert tags == ["dog", "cat"]  # beach below threshold, ordered by score
