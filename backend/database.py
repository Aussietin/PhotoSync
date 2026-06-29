from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Run Alembic migrations to head so schema is always current."""
    import asyncio
    from alembic.config import Config
    from alembic import command

    def _run_migrations():
        import os
        ini_path = os.path.join(os.path.dirname(__file__), "alembic.ini")
        cfg = Config(ini_path)
        cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "alembic"))
        cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        command.upgrade(cfg, "head")

    await asyncio.get_event_loop().run_in_executor(None, _run_migrations)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
