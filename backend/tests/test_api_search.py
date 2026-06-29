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

import pytest
from sqlalchemy import select

from models.photo import Photo, Tag


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
