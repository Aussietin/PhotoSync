"""Single-photo routes. Registered LAST: `/{photo_id}` would otherwise
swallow fixed paths like `/timeline`."""
import json
import logging
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask
from sqlalchemy import select, func, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from database import get_db
from models.photo import Photo, DeletionLog
from routes.photos.cleanup import _remove_photo_files
from routes.photos.serialize import _serialize

router = APIRouter()


# ── Per-photo AI tagging ──────────────────────────────────────────────────────

@router.post("/{photo_id}/tag")
async def tag_single_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    """Run AI tagging on a single photo on demand. Returns the generated tags."""
    from services.ai_tagger import tag_photo
    from sqlalchemy.orm import selectinload as _sil

    photo = await db.get(Photo, photo_id, options=[_sil(Photo.tags)])
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    tags = await tag_photo(db, photo)
    return {"id": photo_id, "tags": tags, "description": photo.ai_description}


# ── Original file ─────────────────────────────────────────────────────────────

@router.get("/{photo_id}/original")
async def get_original(photo_id: int, db: AsyncSession = Depends(get_db)):
    """Stream the full-resolution original file.

    Works for *both* ingestion paths: browser uploads (stored under uploads/)
    and folder imports (referenced in place, outside uploads/). Serving through
    the API means it's covered by the auth guard and resolves regardless of
    where the file physically lives — unlike the /uploads static mount, which
    only sees copied-in files.
    """
    photo = await db.get(Photo, photo_id)
    if not photo or not photo.file_path or not Path(photo.file_path).exists():
        raise HTTPException(status_code=404, detail="Original file not found")
    return FileResponse(
        photo.file_path,
        media_type=photo.mime_type or "application/octet-stream",
        filename=photo.original_filename,
    )


# ── Single photo (kept last so specific-path routes take priority) ────────────

@router.get("/{photo_id}")
async def get_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id, options=[selectinload(Photo.tags)])
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return _serialize(photo)


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo.deleted_at = datetime.utcnow()
    photo.deleted_batch = None  # manual trash, not part of a cleanup batch (see cleanup.bulk_delete)
    await db.commit()


@router.delete("/{photo_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def permanent_delete(photo_id: int, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    # Permanent delete is the step *after* trash. Allowing it on a live photo
    # meant one call took it straight from the library to gone, uploaded file
    # included, skipping the trash / undo safety net entirely.
    if photo.deleted_at is None:
        raise HTTPException(status_code=409, detail="Move the photo to Trash before deleting it permanently")
    _remove_photo_files(photo)
    await db.delete(photo)
    await db.commit()


@router.post("/{photo_id}/restore")
async def restore_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo.deleted_at = None
    photo.deleted_batch = None
    await db.commit()
    return {"id": photo.id, "restored": True}


@router.post("/{photo_id}/favorite")
async def toggle_favorite(photo_id: int, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo.is_favorite = not photo.is_favorite
    await db.commit()
    return {"id": photo.id, "is_favorite": photo.is_favorite}


class NotesIn(BaseModel):
    notes: str


@router.patch("/{photo_id}/notes")
async def update_notes(photo_id: int, body: NotesIn, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo.notes = body.notes
    await db.commit()
    return {"id": photo.id, "notes": photo.notes}
