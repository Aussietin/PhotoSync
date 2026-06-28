from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Text, Boolean, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


# Album <-> Photo many-to-many junction
photo_albums = Table(
    "photo_albums",
    Base.metadata,
    Column("photo_id", Integer, ForeignKey("photos.id", ondelete="CASCADE"), primary_key=True),
    Column("album_id", Integer, ForeignKey("albums.id", ondelete="CASCADE"), primary_key=True),
)


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    preview_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # Dimensions
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # EXIF / temporal metadata
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    camera_make: Mapped[str | None] = mapped_column(String(128), nullable=True)
    camera_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gps_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_lon: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Deduplication
    perceptual_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("photos.id"), nullable=True)

    # AI
    ai_tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    ai_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Quality score (0–1): higher = sharper + better exposed
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Classification
    is_screenshot: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_dark: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_overexposed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_low_res: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Burst grouping (photos taken seconds apart + visually similar share an id)
    burst_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    # User features
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Soft delete (deleted_batch links a cleanup run for one-click undo)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    deleted_batch: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    # Housekeeping
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tags: Mapped[list["Tag"]] = relationship("Tag", back_populates="photo", cascade="all, delete-orphan")
    albums: Mapped[list["Album"]] = relationship("Album", secondary=photo_albums, back_populates="photos")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    photo_id: Mapped[int] = mapped_column(Integer, ForeignKey("photos.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")  # "manual" | "ai"
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    photo: Mapped["Photo"] = relationship("Photo", back_populates="tags")


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_photo_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("photos.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    photos: Mapped[list["Photo"]] = relationship("Photo", secondary=photo_albums, back_populates="albums")


class Job(Base):
    """A long-running background task (import / analyze / rescan) with progress."""
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending|running|done|error
    total: Mapped[int] = mapped_column(Integer, default=0)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DeletionLog(Base):
    """Audit record for each cleanup/delete batch, enabling one-click undo."""
    __tablename__ = "deletion_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(128), default="manual")
    count: Mapped[int] = mapped_column(Integer, default=0)
    undone: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
