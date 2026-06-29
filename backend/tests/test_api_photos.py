"""
Integration tests for core photo CRUD operations:
  - list (pagination, filters, sort)
  - soft delete + restore
  - favorite toggle
  - bulk operations
  - trash endpoint
"""
from datetime import datetime

import pytest
from sqlalchemy import select

from models.photo import Photo


# ── Helpers ───────────────────────────────────────────────────────────────────

def _photo(**kwargs) -> Photo:
    defaults = dict(
        filename="img.jpg",
        original_filename="img.jpg",
        file_path=f"/fake/{abs(hash(str(kwargs)))}.jpg",
        file_size=512,
        mime_type="image/jpeg",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return Photo(**defaults)


async def _seed(session, photos):
    for p in photos:
        session.add(p)
    await session.commit()
    for p in photos:
        await session.refresh(p)
    return photos


# ── List ──────────────────────────────────────────────────────────────────────

async def test_list_empty(client):
    resp = await client.get("/api/photos")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["photos"] == []


async def test_list_returns_live_photos(client, db_session):
    live = _photo(file_path="/fake/live.jpg")
    trashed = _photo(file_path="/fake/trash.jpg", deleted_at=datetime.utcnow())
    await _seed(db_session, [live, trashed])

    resp = await client.get("/api/photos")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["photos"][0]["id"] == live.id


async def test_list_excludes_duplicates_by_default(client, db_session):
    orig = _photo(file_path="/fake/orig.jpg")
    dup = _photo(file_path="/fake/dup.jpg", is_duplicate=True)
    await _seed(db_session, [orig, dup])

    resp = await client.get("/api/photos")
    assert resp.json()["total"] == 1

    resp = await client.get("/api/photos?include_duplicates=true")
    assert resp.json()["total"] == 2


async def test_duplicates_endpoint_serializes_with_tags(client, db_session):
    """Regression: /duplicates must eager-load tags. _serialize reads p.tags,
    and async lazy-load raises MissingGreenlet, so a duplicate with a tag (or
    any duplicate at all) used to 500 here."""
    from models.photo import Tag

    orig = _photo(file_path="/fake/orig.jpg")
    dup = _photo(file_path="/fake/dup.jpg", is_duplicate=True)
    dup.tags.append(Tag(name="beach", source="manual"))
    await _seed(db_session, [orig, dup])

    resp = await client.get("/api/photos/duplicates")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["duplicates"]) == 1
    assert body["duplicates"][0]["id"] == dup.id
    assert body["duplicates"][0]["tags"][0]["name"] == "beach"


async def test_list_favorites_filter(client, db_session):
    fav = _photo(file_path="/fake/fav.jpg", is_favorite=True)
    plain = _photo(file_path="/fake/plain.jpg")
    await _seed(db_session, [fav, plain])

    resp = await client.get("/api/photos?favorites_only=true")
    assert resp.json()["total"] == 1
    assert resp.json()["photos"][0]["is_favorite"] is True


async def test_list_pagination(client, db_session):
    photos = [_photo(file_path=f"/fake/pg_{i}.jpg") for i in range(10)]
    await _seed(db_session, photos)

    resp = await client.get("/api/photos?per_page=3&page=1")
    body = resp.json()
    assert body["total"] == 10
    assert len(body["photos"]) == 3

    resp2 = await client.get("/api/photos?per_page=3&page=4")
    assert len(resp2.json()["photos"]) == 1  # 10th item


# ── Single photo ──────────────────────────────────────────────────────────────

async def test_get_photo_not_found(client):
    resp = await client.get("/api/photos/999")
    assert resp.status_code == 404


async def test_get_photo(client, db_session):
    p = _photo(file_path="/fake/single.jpg")
    await _seed(db_session, [p])

    resp = await client.get(f"/api/photos/{p.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == p.id


# ── Soft delete / restore ─────────────────────────────────────────────────────

async def test_soft_delete(client, db_session):
    p = _photo(file_path="/fake/del.jpg")
    await _seed(db_session, [p])

    resp = await client.delete(f"/api/photos/{p.id}")
    assert resp.status_code == 204

    await db_session.refresh(p)
    assert p.deleted_at is not None

    # Should not appear in main list
    list_resp = await client.get("/api/photos")
    assert list_resp.json()["total"] == 0


async def test_restore_photo(client, db_session):
    p = _photo(file_path="/fake/restore.jpg", deleted_at=datetime.utcnow())
    await _seed(db_session, [p])

    resp = await client.post(f"/api/photos/{p.id}/restore")
    assert resp.status_code == 200
    assert resp.json()["restored"] is True

    await db_session.refresh(p)
    assert p.deleted_at is None


async def test_trash_list(client, db_session):
    trashed = _photo(file_path="/fake/trash2.jpg", deleted_at=datetime.utcnow())
    live = _photo(file_path="/fake/live2.jpg")
    await _seed(db_session, [trashed, live])

    resp = await client.get("/api/photos/trash")
    assert resp.status_code == 200
    photos = resp.json()["photos"]
    assert len(photos) == 1
    assert photos[0]["id"] == trashed.id


# ── Favorite toggle ───────────────────────────────────────────────────────────

async def test_favorite_toggle(client, db_session):
    p = _photo(file_path="/fake/fav_toggle.jpg")
    await _seed(db_session, [p])

    resp = await client.post(f"/api/photos/{p.id}/favorite")
    assert resp.status_code == 200
    assert resp.json()["is_favorite"] is True

    resp2 = await client.post(f"/api/photos/{p.id}/favorite")
    assert resp2.json()["is_favorite"] is False


# ── Bulk operations ───────────────────────────────────────────────────────────

async def test_bulk_delete(client, db_session):
    p1 = _photo(file_path="/fake/bd1.jpg")
    p2 = _photo(file_path="/fake/bd2.jpg")
    p3 = _photo(file_path="/fake/bd3.jpg")
    await _seed(db_session, [p1, p2, p3])

    resp = await client.post("/api/photos/bulk/delete", json={"photo_ids": [p1.id, p2.id]})
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 2

    await db_session.refresh(p1)
    await db_session.refresh(p3)
    assert p1.deleted_at is not None
    assert p3.deleted_at is None


async def test_bulk_favorite(client, db_session):
    p1 = _photo(file_path="/fake/bf1.jpg")
    p2 = _photo(file_path="/fake/bf2.jpg")
    await _seed(db_session, [p1, p2])

    resp = await client.post("/api/photos/bulk/favorite", json={"photo_ids": [p1.id, p2.id]})
    assert resp.status_code == 200
    assert resp.json()["favorited"] == 2

    await db_session.refresh(p1)
    assert p1.is_favorite is True


async def test_bulk_restore(client, db_session):
    p1 = _photo(file_path="/fake/br1.jpg", deleted_at=datetime.utcnow())
    p2 = _photo(file_path="/fake/br2.jpg", deleted_at=datetime.utcnow())
    await _seed(db_session, [p1, p2])

    resp = await client.post("/api/photos/bulk/restore", json={"photo_ids": [p1.id, p2.id]})
    assert resp.status_code == 200
    assert resp.json()["restored"] == 2

    await db_session.refresh(p1)
    assert p1.deleted_at is None


# ── Notes ─────────────────────────────────────────────────────────────────────

async def test_update_notes(client, db_session):
    p = _photo(file_path="/fake/notes.jpg")
    await _seed(db_session, [p])

    resp = await client.patch(f"/api/photos/{p.id}/notes", json={"notes": "keeper!"})
    assert resp.status_code == 200
    assert resp.json()["notes"] == "keeper!"

    await db_session.refresh(p)
    assert p.notes == "keeper!"


# ── Download ZIP ───────────────────────────────────────────────────────────────

async def test_download_zip_empty_ids_returns_400(client):
    resp = await client.post("/api/photos/download-zip", json={"photo_ids": []})
    assert resp.status_code == 400


async def test_download_zip_unknown_ids_returns_404(client):
    resp = await client.post("/api/photos/download-zip", json={"photo_ids": [9999, 8888]})
    assert resp.status_code == 404


async def test_download_zip_disk_based(client, db_session, tmp_path):
    """download-zip writes to a temp file, returns application/zip, no photo cap."""
    import zipfile
    import io

    # Create real image files on disk so zipfile.write succeeds.
    files = []
    photos = []
    for i in range(3):
        fp = tmp_path / f"real_{i}.jpg"
        fp.write_bytes(b"FAKEJPEG" * 10)
        p = _photo(
            file_path=str(fp),
            filename=f"real_{i}.jpg",
            original_filename=f"photo_{i}.jpg",
        )
        photos.append(p)
        files.append(fp)
    await _seed(db_session, photos)

    resp = await client.post(
        "/api/photos/download-zip",
        json={"photo_ids": [p.id for p in photos]},
    )
    assert resp.status_code == 200
    assert "application/zip" in resp.headers["content-type"]

    # Verify the archive contains all three files.
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = zf.namelist()
    assert len(names) == 3
    assert set(names) == {"photo_0.jpg", "photo_1.jpg", "photo_2.jpg"}


async def test_download_zip_deduplicates_filenames(client, db_session, tmp_path):
    """Two photos with the same original_filename get distinct archive names."""
    import zipfile
    import io

    fp1 = tmp_path / "a.jpg"
    fp2 = tmp_path / "b.jpg"
    fp1.write_bytes(b"AAA")
    fp2.write_bytes(b"BBB")

    p1 = _photo(file_path=str(fp1), filename="a.jpg", original_filename="img.jpg")
    p2 = _photo(file_path=str(fp2), filename="b.jpg", original_filename="img.jpg")
    await _seed(db_session, [p1, p2])

    resp = await client.post(
        "/api/photos/download-zip",
        json={"photo_ids": [p1.id, p2.id]},
    )
    assert resp.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = zf.namelist()
    # Both entries present, no collision.
    assert len(names) == 2
    assert len(set(names)) == 2
