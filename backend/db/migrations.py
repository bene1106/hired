"""Programmatic interface to Alembic, used by FastAPI startup and tests."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from alembic import command
from db.session import resolve_db_url

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
ALEMBIC_DIR = ALEMBIC_INI.parent / "alembic"


def alembic_config() -> Config:
    """Build an Alembic Config that uses the same DB URL as the app."""
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", resolve_db_url())
    return cfg


def run_migrations() -> None:
    """Apply all pending migrations to the configured database (idempotent)."""
    command.upgrade(alembic_config(), "head")
