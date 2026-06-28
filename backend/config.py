from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "PhotoSync"
    DATABASE_URL: str = "sqlite+aiosqlite:///./photosync.db"
    UPLOAD_DIR: str = str(Path(__file__).parent / "uploads")
    THUMBNAIL_DIR: str = str(Path(__file__).parent / "thumbnails")
    PREVIEW_DIR: str = str(Path(__file__).parent / "previews")
    THUMBNAIL_SIZE: tuple[int, int] = (400, 400)
    PREVIEW_SIZE: tuple[int, int] = (1600, 1600)  # web-friendly JPEG for the viewer
    MAX_UPLOAD_SIZE_MB: int = 50
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Quality/classification thresholds (0–1 brightness scale)
    DARK_THRESHOLD: float = 0.18
    OVEREXPOSED_THRESHOLD: float = 0.92
    LOW_RES_MEGAPIXELS: float = 0.5  # below this is "low res"

    # Trash retention: photos in trash older than this are eligible for auto-empty
    TRASH_RETENTION_DAYS: int = 30

    # Optional API token. When set (non-empty), all /api routes require
    # `X-API-Token: <token>`. Empty = open (default, for localhost use).
    API_TOKEN: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
