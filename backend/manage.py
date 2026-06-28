#!/usr/bin/env python3
"""
CLI helper for common Alembic operations.

Usage:
  python manage.py migrate          # upgrade to head
  python manage.py makemigration    # autogenerate a new migration (prompts for message)
  python manage.py stamp            # stamp existing DB as head (use once on pre-Alembic DBs)
  python manage.py history          # print migration history
  python manage.py current          # show current revision
"""
import sys
import os

from alembic.config import Config
from alembic import command

BASE_DIR = os.path.dirname(__file__)


def _cfg() -> Config:
    cfg = Config(os.path.join(BASE_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BASE_DIR, "alembic"))
    # Pull DB URL from settings so it's always the single source of truth
    from config import settings
    cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    return cfg


def migrate():
    command.upgrade(_cfg(), "head")


def makemigration(msg: str):
    command.revision(_cfg(), message=msg, autogenerate=True)


def stamp():
    command.stamp(_cfg(), "head")


def history():
    command.history(_cfg())


def current():
    command.current(_cfg())


COMMANDS = {
    "migrate": migrate,
    "stamp": stamp,
    "history": history,
    "current": current,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS and sys.argv[1] != "makemigration":
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "makemigration":
        msg = sys.argv[2] if len(sys.argv) > 2 else input("Migration message: ")
        makemigration(msg)
    else:
        COMMANDS[cmd]()
