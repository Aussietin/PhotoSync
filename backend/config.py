from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "PhotoSync"
    DATABASE_URL: str = "sqlite+aiosqlite:///./photosync.db"
    UPLOAD_DIR: str = str(Path(__file__).parent / "uploads")
    THUMBNAIL_DIR: str = str(Path(__file__).parent / "thumbnails")
    THUMBNAIL_SIZE: tuple[int, int] = (400, 400)
    MAX_UPLOAD_SIZE_MB: int = 50
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
