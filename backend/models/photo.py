from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
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
    ai_tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array stored as text
    ai_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Housekeeping
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tags: Mapped[list["Tag"]] = relationship("Tag", back_populates="photo", cascade="all, delete-orphan")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    photo_id: Mapped[int] = mapped_column(Integer, ForeignKey("photos.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")  # "manual" | "ai"
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    photo: Mapped["Photo"] = relationship("Photo", back_populates="tags")
