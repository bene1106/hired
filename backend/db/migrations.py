"""Programmatic interface to Alembic, used by FastAPI startup and tests."""

from __future__ import annotations

import sys
from pathlib import Path

from alembic.config import Config

from alembic import command
from db.session import resolve_db_url


def _resource_root() -> Path:
    """Return the directory that holds ``alembic.ini`` and the ``alembic/`` tree.

    In normal source-tree runs this is the ``backend/`` directory. When
    the sidecar is bundled by PyInstaller (one-file mode) the same files
    are extracted under ``sys._MEIPASS`` instead.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


ALEMBIC_INI = _resource_root() / "alembic.ini"
ALEMBIC_DIR = _resource_root() / "alembic"


def alembic_config() -> Config:
    """Build an Alembic Config that uses the same DB URL as the app."""
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", resolve_db_url())
    return cfg


def run_migrations() -> None:
    """Apply all pending migrations to the configured database (idempotent)."""
    command.upgrade(alembic_config(), "head")
