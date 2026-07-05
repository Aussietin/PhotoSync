"""
Safety tests for destructive file removal.

The core promise: emptying Trash or permanently deleting a photo must NEVER
destroy an in-place folder-import original (frequently the user's only copy).
Only PhotoSync-managed files — copies under uploads/, plus generated thumbnails
and previews — may be removed from disk.
"""
import uuid
from datetime import datetime
from pathlib import Path

from config import settings
from models.photo import Photo


def _write(path: Path, data: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


async def _seed(session, photos):
    for p in photos:
        session.add(p)
    await session.commit()
    return photos


async def test_empty_trash_preserves_in_place_originals(client, db_session, tmp_path):
    stem = uuid.uuid4().hex

    # An in-place folder-import original living OUTSIDE uploads/ — the user's
    # source file. This must survive.
    in_place = _write(tmp_path / "DCIM" / "IMG_0001.JPG")
    # A browser-uploaded copy living under uploads/ — PhotoSync made it, so it
    # may be cleaned up.
    uploaded = _write(Path(settings.UPLOAD_DIR) / f"{stem}.jpg")
    # Managed thumbnail/preview — always removable.
    thumb = _write(Path(settings.THUMBNAIL_DIR) / f"{stem}_thumb.jpg")
    preview = _write(Path(settings.PREVIEW_DIR) / f"{stem}_preview.jpg")

    await _seed(db_session, [
        Photo(filename="IMG_0001.JPG", original_filename="IMG_0001.JPG",
              file_path=str(in_place), thumbnail_path=str(thumb),
              preview_path=str(preview), file_size=1, mime_type="image/jpeg",
              deleted_at=datetime.utcnow()),
        Photo(filename=f"{stem}.jpg", original_filename="up.jpg",
              file_path=str(uploaded), file_size=1, mime_type="image/jpeg",
              deleted_at=datetime.utcnow()),
    ])

    resp = await client.post("/api/photos/empty-trash")
    assert resp.status_code == 200
    assert resp.json()["permanently_deleted"] == 2

    # The user's in-place original is untouched...
    assert in_place.exists(), "in-place folder-import original must NOT be deleted"
    # ...while PhotoSync-managed files are gone.
    assert not uploaded.exists()
    assert not thumb.exists()
    assert not preview.exists()

    # Trash is now empty.
    trash = (await client.get("/api/photos/trash")).json()
    assert trash["photos"] == []


async def test_permanent_delete_preserves_in_place_original(client, db_session, tmp_path):
    in_place = _write(tmp_path / "IMG_0002.JPG")
    p, = await _seed(db_session, [
        Photo(filename="IMG_0002.JPG", original_filename="IMG_0002.JPG",
              file_path=str(in_place), file_size=1, mime_type="image/jpeg",
              deleted_at=datetime.utcnow()),
    ])

    resp = await client.delete(f"/api/photos/{p.id}/permanent")
    assert resp.status_code == 204
    assert in_place.exists(), "permanent-delete must NOT remove an in-place original"
