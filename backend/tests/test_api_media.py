"""
Tests for video ingestion and large-file flagging (the space-hog cull path).
"""
import io
from datetime import datetime

from config import settings
from models.photo import Photo

MB = 1024 * 1024


def _photo(**kw) -> Photo:
    d = dict(
        filename="x.jpg", original_filename="x.jpg",
        file_path=f"/fake/{abs(hash(str(kw)))}.x", file_size=1024,
        mime_type="image/jpeg", created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    d.update(kw)
    return Photo(**d)


async def _seed(session, photos):
    for p in photos:
        session.add(p)
    await session.commit()
    for p in photos:
        await session.refresh(p)
    return photos


async def test_large_flag_summary_listing_and_cleanup(client, db_session):
    big = settings.LARGE_FILE_MB * MB + 1
    await _seed(db_session, [
        _photo(file_path="/fake/big.mov", original_filename="clip.mov",
               mime_type="video/quicktime", file_size=big),
        _photo(file_path="/fake/small.jpg", file_size=2 * MB,
               camera_make="Apple", camera_model="iPhone 15"),
    ])

    # Cleanup summary counts the large file as its own category.
    summary = (await client.get("/api/photos/cleanup-summary")).json()
    assert summary["large"]["count"] == 1
    assert summary["large_threshold_mb"] == settings.LARGE_FILE_MB

    # Dedicated /large endpoint lists biggest-first with video/large flags set.
    large = (await client.get("/api/photos/large")).json()
    assert large["total"] == 1
    p = large["photos"][0]
    assert p["is_video"] is True
    assert p["is_large"] is True
    assert p["is_meme"] is False  # a video must NOT be mistaken for a meme/received

    # One-click cull trashes only the large file; the normal photo is untouched.
    res = (await client.post("/api/photos/cleanup", json={"large": True})).json()
    assert res["deleted"] == 1
    listing = (await client.get("/api/photos")).json()
    assert listing["total"] == 1


async def test_video_upload_is_tracked_without_thumbnail(client):
    res = await client.post(
        "/api/photos/upload",
        files={"files": ("movie.mov", io.BytesIO(b"\x00\x00fakevideo"), "video/quicktime")},
    )
    assert res.status_code == 201
    listing = (await client.get("/api/photos")).json()
    vid = next(p for p in listing["photos"] if p["filename"] == "movie.mov")
    assert vid["is_video"] is True
    assert vid["thumbnail_url"] is None
