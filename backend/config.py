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
    # Allowed browser origins, comma-separated. Override in .env, e.g.
    #   CORS_ORIGINS=http://localhost:5173,http://192.168.1.20:5173
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        """CORS_ORIGINS parsed into a list for the CORS middleware."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Quality/classification thresholds (0–1 brightness scale)
    DARK_THRESHOLD: float = 0.18
    OVEREXPOSED_THRESHOLD: float = 0.92
    LOW_RES_MEGAPIXELS: float = 0.5  # below this is "low res"

    # Trash retention: photos in trash older than this are eligible for auto-empty
    TRASH_RETENTION_DAYS: int = 30

    # Optional API token. When set (non-empty), all /api routes require
    # `X-API-Token: <token>`. Empty = open (default, for localhost use).
    API_TOKEN: str = ""

    # ── Local AI (CLIP) ──────────────────────────────────────────────────────
    # Semantic search + zero-shot tagging run fully on-device via a local CLIP
    # model — no data ever leaves the machine, no API key, no cost. The model is
    # an OPTIONAL dependency (pip install -r requirements-ai.txt). If it isn't
    # installed the app still runs and tagging falls back to the colour heuristic.
    CLIP_MODEL: str = "clip-ViT-B-32"  # sentence-transformers model id (~350MB)
    # A zero-shot tag is kept when image↔label cosine similarity exceeds this.
    AI_TAG_THRESHOLD: float = 0.22
    AI_MAX_TAGS: int = 8

    class Config:
        env_file = ".env"


settings = Settings()
