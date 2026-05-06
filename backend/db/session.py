"""SQLAlchemy engine and session factory.

The default DB lives at ``~/.hired/data.db``; tests and tooling can override
the location by setting ``HIRED_DB_URL`` (e.g. ``sqlite:///./scratch.db``).
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
    """SQLite ignores ON DELETE CASCADE unless foreign_keys=ON is set per connection."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


DEFAULT_DB_DIR = Path.home() / ".hired"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "data.db"


def resolve_db_url() -> str:
    """Return the configured database URL, creating the default dir if needed."""
    override = os.environ.get("HIRED_DB_URL")
    if override:
        return override
    DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_DB_PATH}"


def make_engine(url: str | None = None) -> Engine:
    return create_engine(url or resolve_db_url(), future=True)


_engine: Engine | None = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, future=True)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


def reset_engine() -> None:
    """Dispose and clear the cached engine. Used by tests after env changes."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def get_session() -> Session:
    return SessionLocal(bind=get_engine())


def db_ping() -> bool:
    """Run ``SELECT 1`` against the configured DB. Raises on connection failure."""
    with get_engine().connect() as conn:
        return conn.execute(text("SELECT 1")).scalar() == 1
