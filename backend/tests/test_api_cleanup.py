"""
Integration tests for the mass-cleanup flow:
  - cleanup-summary counts correctly
  - POST /cleanup trashes the right photos and returns a batch token
  - POST /undo-cleanup/{batch} restores them
  - Favorites are never trashed
  - No-category request is rejected
"""
from datetime import datetime

import pytest
from models.photo import Photo, DeletionLog


# ── Helpers ───────────────────────────────────────────────────────────────────

def _photo(**kwargs) -> Photo:
    defaults = dict(
        filename="test.jpg",
        original_filename="test.jpg",
        file_path=f"/fake/{id(kwargs)}.jpg",
        file_size=1024,
        mime_type="image/jpeg",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return Photo(**defaults)


async def _seed(session, photos: list[Photo]):
    for p in photos:
        session.add(p)
    await session.commit()
    for p in photos:
        await session.refresh(p)
    return photos


# ── cleanup-summary ───────────────────────────────────────────────────────────

async def test_cleanup_summary_counts(client, db_session):
    # camera_make="Apple" = real iPhone shot, should NOT match meme filter
    await _seed(db_session, [
        _photo(file_path="/fake/s1.jpg", is_screenshot=True, camera_make="Apple"),
        _photo(file_path="/fake/s2.jpg", is_screenshot=True, camera_make="Apple"),
        _photo(file_path="/fake/d1.jpg", is_duplicate=True, camera_make="Apple"),
        _photo(file_path="/fake/n1.jpg", camera_make="Apple"),  # normal iPhone shot
    ])

    resp = await client.get("/api/photos/cleanup-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["screenshots"]["count"] == 2
    assert data["duplicates"]["count"] == 1
    assert data["memes"]["count"] == 0
    assert data["total_reclaimable"]["count"] == 3


async def test_cleanup_summary_excludes_favorites(client, db_session):
    await _seed(db_session, [
        _photo(file_path="/fake/sf.jpg", is_screenshot=True, is_favorite=True),
        _photo(file_path="/fake/s.jpg", is_screenshot=True),
    ])

    resp = await client.get("/api/photos/cleanup-summary")
    assert resp.status_code == 200
    assert resp.json()["screenshots"]["count"] == 1  # favourite not counted


async def test_cleanup_summary_excludes_already_trashed(client, db_session):
    await _seed(db_session, [
        _photo(file_path="/fake/st.jpg", is_screenshot=True, deleted_at=datetime.utcnow()),
        _photo(file_path="/fake/sl.jpg", is_screenshot=True),
    ])

    resp = await client.get("/api/photos/cleanup-summary")
    assert resp.status_code == 200
    assert resp.json()["screenshots"]["count"] == 1


# ── POST /cleanup ─────────────────────────────────────────────────────────────

async def test_cleanup_trashes_screenshots(client, db_session):
    live = _photo(file_path="/fake/cl_s.jpg", is_screenshot=True)
    normal = _photo(file_path="/fake/cl_n.jpg")
    await _seed(db_session, [live, normal])

    resp = await client.post("/api/photos/cleanup", json={"screenshots": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["deleted"] == 1
    assert "batch" in body

    # Refresh from DB
    await db_session.refresh(live)
    await db_session.refresh(normal)
    assert live.deleted_at is not None
    assert normal.deleted_at is None


async def test_cleanup_trashes_duplicates_only(client, db_session):
    dup = _photo(file_path="/fake/cl_d.jpg", is_duplicate=True)
    orig = _photo(file_path="/fake/cl_o.jpg")
    await _seed(db_session, [dup, orig])

    resp = await client.post("/api/photos/cleanup", json={"duplicates": True})
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 1

    await db_session.refresh(dup)
    assert dup.deleted_at is not None


async def test_cleanup_skips_favorites(client, db_session):
    fav = _photo(file_path="/fake/cl_fav.jpg", is_screenshot=True, is_favorite=True)
    normal = _photo(file_path="/fake/cl_norm.jpg", is_screenshot=True)
    await _seed(db_session, [fav, normal])

    resp = await client.post("/api/photos/cleanup", json={"screenshots": True})
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 1

    await db_session.refresh(fav)
    assert fav.deleted_at is None  # favourite survived


async def test_cleanup_low_quality_filter(client, db_session):
    bad = _photo(file_path="/fake/cl_bad.jpg", quality_score=0.1)
    ok = _photo(file_path="/fake/cl_ok.jpg", quality_score=0.8)
    no_score = _photo(file_path="/fake/cl_ns.jpg", quality_score=None)
    await _seed(db_session, [bad, ok, no_score])

    resp = await client.post("/api/photos/cleanup", json={"max_quality": 0.3})
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 1  # only bad qualifies

    await db_session.refresh(bad)
    await db_session.refresh(ok)
    await db_session.refresh(no_score)
    assert bad.deleted_at is not None
    assert ok.deleted_at is None
    assert no_score.deleted_at is None


async def test_cleanup_meme_filter(client, db_session):
    """No camera EXIF + not screenshot = meme/received image."""
    meme = _photo(file_path="/fake/meme.jpg")  # no camera_make → meme
    real = _photo(file_path="/fake/real.jpg", camera_make="Apple", camera_model="iPhone 15")
    screenshot = _photo(file_path="/fake/scr.jpg", is_screenshot=True)  # excluded from memes
    await _seed(db_session, [meme, real, screenshot])

    resp = await client.get("/api/photos/cleanup-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["memes"]["count"] == 1  # only the no-EXIF non-screenshot photo

    resp2 = await client.post("/api/photos/cleanup", json={"memes": True})
    assert resp2.status_code == 200
    assert resp2.json()["deleted"] == 1

    await db_session.refresh(meme)
    await db_session.refresh(real)
    await db_session.refresh(screenshot)
    assert meme.deleted_at is not None
    assert real.deleted_at is None
    assert screenshot.deleted_at is None  # screenshot not caught by meme filter


async def test_cleanup_no_category_rejected(client, db_session):
    resp = await client.post("/api/photos/cleanup", json={})
    assert resp.status_code == 400


async def test_cleanup_logs_deletion(client, db_session):
    from sqlalchemy import select

    await _seed(db_session, [_photo(file_path="/fake/cl_log.jpg", is_screenshot=True)])
    resp = await client.post("/api/photos/cleanup", json={"screenshots": True})
    assert resp.status_code == 200
    batch = resp.json()["batch"]

    logs = (await db_session.execute(select(DeletionLog).where(DeletionLog.batch == batch))).scalars().all()
    assert len(logs) == 1
    assert logs[0].count == 1


# ── POST /undo-cleanup/{batch} ────────────────────────────────────────────────

async def test_undo_cleanup_restores_photos(client, db_session):
    await _seed(db_session, [
        _photo(file_path="/fake/undo_a.jpg", is_screenshot=True),
        _photo(file_path="/fake/undo_b.jpg", is_screenshot=True),
    ])

    cleanup_resp = await client.post("/api/photos/cleanup", json={"screenshots": True})
    batch = cleanup_resp.json()["batch"]
    assert cleanup_resp.json()["deleted"] == 2

    undo_resp = await client.post(f"/api/photos/undo-cleanup/{batch}")
    assert undo_resp.status_code == 200
    assert undo_resp.json()["restored"] == 2

    # All photos should be live again
    resp = await client.get("/api/photos?include_duplicates=true")
    data = resp.json()
    assert data["total"] == 2


async def test_undo_cleanup_unknown_batch(client, db_session):
    resp = await client.post("/api/photos/undo-cleanup/nonexistent-batch-id")
    assert resp.status_code == 404


# ── cleanup-history ───────────────────────────────────────────────────────────

async def test_cleanup_history_returned(client, db_session):
    await _seed(db_session, [_photo(file_path="/fake/hist.jpg", is_duplicate=True)])
    await client.post("/api/photos/cleanup", json={"duplicates": True})

    resp = await client.get("/api/photos/cleanup-history")
    assert resp.status_code == 200
    history = resp.json()["history"]
    assert len(history) >= 1
    assert history[0]["count"] == 1
