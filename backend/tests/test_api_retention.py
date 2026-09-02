"""
Trash retention sweep.

TRASH_AUTO_EMPTY (off by default) lets a startup sweep permanently clear photos
that have sat in Trash longer than TRASH_RETENTION_DAYS. It must:
  - do nothing while disabled,
  - remove only photos past the cutoff (recent trash stays),
  - never destroy an in-place folder-import original.
"""
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from config import settings
from models.photo import Photo
from routes.photos import sweep_expired_trash


def _write(path: Path, data: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


async def _seed(session, photos):
    for p in photos:
        session.add(p)
    await session.commit()
    return photos


async def test_sweep_is_noop_when_disabled(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "TRASH_AUTO_EMPTY", False)
    monkeypatch.setattr(settings, "TRASH_RETENTION_DAYS", 30)

    await _seed(db_session, [
        Photo(filename="old.jpg", original_filename="old.jpg", file_path="x/old.jpg",
              file_size=1, mime_type="image/jpeg",
              deleted_at=datetime.utcnow() - timedelta(days=99)),
    ])

    assert await sweep_expired_trash() == 0
    remaining = (await client.get("/api/photos/trash")).json()["photos"]
    assert len(remaining) == 1


async def test_sweep_removes_only_expired(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "TRASH_AUTO_EMPTY", True)
    monkeypatch.setattr(settings, "TRASH_RETENTION_DAYS", 30)

    await _seed(db_session, [
        Photo(filename="old.jpg", original_filename="old.jpg", file_path="x/old.jpg",
              file_size=1, mime_type="image/jpeg",
              deleted_at=datetime.utcnow() - timedelta(days=45)),
        Photo(filename="recent.jpg", original_filename="recent.jpg", file_path="x/recent.jpg",
              file_size=1, mime_type="image/jpeg",
              deleted_at=datetime.utcnow() - timedelta(days=3)),
        Photo(filename="live.jpg", original_filename="live.jpg", file_path="x/live.jpg",
              file_size=1, mime_type="image/jpeg", deleted_at=None),
    ])

    assert await sweep_expired_trash() == 1

    trash = (await client.get("/api/photos/trash")).json()["photos"]
    assert [p["filename"] for p in trash] == ["recent.jpg"]
    lib = (await client.get("/api/photos")).json()
    assert any(p["filename"] == "live.jpg" for p in lib["photos"])


async def test_sweep_preserves_in_place_original(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "TRASH_AUTO_EMPTY", True)
    monkeypatch.setattr(settings, "TRASH_RETENTION_DAYS", 30)
    monkeypatch.setattr(settings, "DELETE_IN_PLACE_ORIGINALS", False)

    stem = uuid.uuid4().hex
    in_place = _write(tmp_path / "DCIM" / "IMG_9001.JPG")
    uploaded = _write(Path(settings.UPLOAD_DIR) / f"{stem}.jpg")

    await _seed(db_session, [
        Photo(filename="IMG_9001.JPG", original_filename="IMG_9001.JPG",
              file_path=str(in_place), file_size=1, mime_type="image/jpeg",
              deleted_at=datetime.utcnow() - timedelta(days=60)),
        Photo(filename=f"{stem}.jpg", original_filename="up.jpg",
              file_path=str(uploaded), file_size=1, mime_type="image/jpeg",
              deleted_at=datetime.utcnow() - timedelta(days=60)),
    ])

    assert await sweep_expired_trash() == 2
    assert in_place.exists(), "in-place folder-import original must survive the sweep"
    assert not uploaded.exists()


async def test_trash_status_reports_expired(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "TRASH_AUTO_EMPTY", True)
    monkeypatch.setattr(settings, "TRASH_RETENTION_DAYS", 30)

    await _seed(db_session, [
        Photo(filename="old.jpg", original_filename="old.jpg", file_path="x/old.jpg",
              file_size=10, mime_type="image/jpeg",
              deleted_at=datetime.utcnow() - timedelta(days=40)),
        Photo(filename="recent.jpg", original_filename="recent.jpg", file_path="x/recent.jpg",
              file_size=20, mime_type="image/jpeg",
              deleted_at=datetime.utcnow() - timedelta(days=1)),
    ])

    status = (await client.get("/api/photos/trash-status")).json()
    assert status["auto_empty_enabled"] is True
    assert status["retention_days"] == 30
    assert status["in_trash"]["count"] == 2
    assert status["expired"]["count"] == 1
    assert status["expired"]["bytes"] == 10
    assert status["oldest_deleted_at"] is not None
