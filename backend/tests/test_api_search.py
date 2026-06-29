"""
Integration tests for GET /api/search.

Covers:
  - keyword search across filename, Tag.name, ai_description, ai_tags
  - date and camera filters
  - tag filter
  - pagination
"""
import json
from datetime import datetime, date
from unittest.mock import patch

import numpy as np
import pytest
from sqlalchemy import select

from models.photo import Photo, Tag
from services import embeddings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _photo(**kwargs) -> Photo:
    defaults = dict(
        filename="img.jpg",
        original_filename="img.jpg",
        file_path=f"/fake/search/{abs(hash(str(kwargs)))}.jpg",
        file_size=512,
        mime_type="image/jpeg",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return Photo(**defaults)


async def _seed(session, rows):
    for r in rows:
        session.add(r)
    await session.commit()
    for r in rows:
        await session.refresh(r)
    return rows


# ── Filename search ────────────────────────────────────────────────────────────

async def test_search_by_filename(client, db_session):
    await _seed(db_session, [
        _photo(file_path="/fake/s/a.jpg", original_filename="sunset_beach.jpg"),
        _photo(file_path="/fake/s/b.jpg", original_filename="birthday_party.jpg"),
    ])
    resp = await client.get("/api/search?q=sunset")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["photos"][0]["filename"] == "sunset_beach.jpg"


# ── Tag search ─────────────────────────────────────────────────────────────────

async def test_search_by_manual_tag(client, db_session):
    p = _photo(file_path="/fake/s/c.jpg", original_filename="hike.jpg")
    await _seed(db_session, [p])
    db_session.add(Tag(photo_id=p.id, name="mountain", source="manual"))
    await db_session.commit()

    resp = await client.get("/api/search?q=mountain")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


async def test_search_by_tag_filter(client, db_session):
    p1 = _photo(file_path="/fake/s/d1.jpg", original_filename="dog.jpg")
    p2 = _photo(file_path="/fake/s/d2.jpg", original_filename="cat.jpg")
    await _seed(db_session, [p1, p2])
    db_session.add(Tag(photo_id=p1.id, name="dog", source="manual"))
    await db_session.commit()

    resp = await client.get("/api/search?tag=dog")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["photos"][0]["filename"] == "dog.jpg"


# ── AI description / ai_tags search ───────────────────────────────────────────

async def test_search_by_ai_description(client, db_session):
    p = _photo(
        file_path="/fake/s/e.jpg",
        original_filename="landscape.jpg",
        ai_description="A misty morning over rolling hills.",
    )
    await _seed(db_session, [p])

    resp = await client.get("/api/search?q=misty")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


async def test_search_by_ai_tags_json(client, db_session):
    p = _photo(
        file_path="/fake/s/f.jpg",
        original_filename="portrait.jpg",
        ai_tags=json.dumps(["portrait", "warm tones", "indoor"]),
    )
    await _seed(db_session, [p])

    resp = await client.get("/api/search?q=warm+tones")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


async def test_search_no_match_returns_empty(client, db_session):
    await _seed(db_session, [_photo(file_path="/fake/s/g.jpg", original_filename="random.jpg")])

    resp = await client.get("/api/search?q=zzznomatch")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


# ── Date filter ────────────────────────────────────────────────────────────────

async def test_search_date_from(client, db_session):
    old = _photo(
        file_path="/fake/s/h1.jpg",
        original_filename="old.jpg",
        taken_at=datetime(2020, 1, 1),
    )
    recent = _photo(
        file_path="/fake/s/h2.jpg",
        original_filename="recent.jpg",
        taken_at=datetime(2024, 6, 1),
    )
    await _seed(db_session, [old, recent])

    resp = await client.get("/api/search?date_from=2023-01-01")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["photos"][0]["filename"] == "recent.jpg"


# ── Camera filter ──────────────────────────────────────────────────────────────

async def test_search_by_camera(client, db_session):
    iphone = _photo(file_path="/fake/s/i1.jpg", original_filename="a.jpg", camera_make="Apple", camera_model="iPhone 14")
    sony = _photo(file_path="/fake/s/i2.jpg", original_filename="b.jpg", camera_make="Sony", camera_model="A7IV")
    await _seed(db_session, [iphone, sony])

    resp = await client.get("/api/search?camera=apple")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["photos"][0]["camera"] == "Apple iPhone 14"


# ── Pagination ─────────────────────────────────────────────────────────────────

async def test_search_pagination(client, db_session):
    photos = [_photo(file_path=f"/fake/s/p{i}.jpg", original_filename=f"photo_{i}.jpg") for i in range(5)]
    await _seed(db_session, photos)

    resp = await client.get("/api/search?per_page=2&page=1")
    assert resp.status_code == 200
    assert len(resp.json()["photos"]) == 2

    resp2 = await client.get("/api/search?per_page=2&page=2")
    assert resp2.status_code == 200
    assert len(resp2.json()["photos"]) == 2


# ── Semantic search (local CLIP, mocked encoder) ────────────────────────────────

def _emb(*vals) -> bytes:
    return embeddings.to_blob(np.array(vals, dtype=np.float32))


async def test_semantic_search_ranks_by_similarity(client, db_session):
    """Photos are returned best-match-first by cosine similarity to the query."""
    near = _photo(file_path="/fake/sem/near.jpg", original_filename="near.jpg",
                  clip_embedding=_emb(1.0, 0.0))
    mid = _photo(file_path="/fake/sem/mid.jpg", original_filename="mid.jpg",
                 clip_embedding=_emb(0.7, 0.7))
    far = _photo(file_path="/fake/sem/far.jpg", original_filename="far.jpg",
                 clip_embedding=_emb(0.0, 1.0))
    await _seed(db_session, [near, mid, far])

    # Query vector points along the first axis → "near" is the best match.
    with patch("services.embeddings.embed_text",
               return_value=np.array([1.0, 0.0], dtype=np.float32)):
        resp = await client.get("/api/search/semantic?q=anything&min_score=0.0")

    assert resp.status_code == 200
    body = resp.json()
    names = [p["filename"] for p in body["photos"]]
    assert names == ["near.jpg", "mid.jpg", "far.jpg"]
    assert body["photos"][0]["score"] >= body["photos"][1]["score"]


async def test_semantic_search_min_score_filters(client, db_session):
    """Results below min_score are excluded."""
    near = _photo(file_path="/fake/sem/n.jpg", original_filename="n.jpg",
                  clip_embedding=_emb(1.0, 0.0))
    far = _photo(file_path="/fake/sem/f.jpg", original_filename="f.jpg",
                 clip_embedding=_emb(0.0, 1.0))
    await _seed(db_session, [near, far])

    with patch("services.embeddings.embed_text",
               return_value=np.array([1.0, 0.0], dtype=np.float32)):
        resp = await client.get("/api/search/semantic?q=x&min_score=0.5")

    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["photos"][0]["filename"] == "n.jpg"


async def test_semantic_search_excludes_deleted_and_duplicates(client, db_session):
    live = _photo(file_path="/fake/sem/live.jpg", original_filename="live.jpg",
                  clip_embedding=_emb(1.0, 0.0))
    trashed = _photo(file_path="/fake/sem/del.jpg", original_filename="del.jpg",
                     clip_embedding=_emb(1.0, 0.0), deleted_at=datetime.utcnow())
    dupe = _photo(file_path="/fake/sem/dup.jpg", original_filename="dup.jpg",
                  clip_embedding=_emb(1.0, 0.0), is_duplicate=True)
    await _seed(db_session, [live, trashed, dupe])

    with patch("services.embeddings.embed_text",
               return_value=np.array([1.0, 0.0], dtype=np.float32)):
        resp = await client.get("/api/search/semantic?q=x&min_score=0.0")

    body = resp.json()
    assert [p["filename"] for p in body["photos"]] == ["live.jpg"]


async def test_semantic_search_no_indexed_photos(client, db_session):
    """With the model available but nothing indexed, returns an empty hinted result."""
    await _seed(db_session, [
        _photo(file_path="/fake/sem/u.jpg", original_filename="u.jpg"),  # no embedding
    ])
    with patch("services.embeddings.embed_text",
               return_value=np.array([1.0, 0.0], dtype=np.float32)):
        resp = await client.get("/api/search/semantic?q=x")

    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert "hint" in body


async def test_semantic_search_model_unavailable(client, db_session):
    """When the CLIP model isn't installed, returns 503 with install guidance."""
    with patch("services.embeddings.embed_text", return_value=None):
        resp = await client.get("/api/search/semantic?q=x")

    assert resp.status_code == 503
    assert "requirements-ai.txt" in resp.json()["detail"]
