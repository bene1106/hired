"""SQLAlchemy engine and session factory.

The default DB lives at ``~/.hired/data.db``; tests and tooling can override
the location by setting ``HIRED_DB_URL`` (e.g. ``sqlite:///./scratch.db``).

v0.3.1: when the default production path is resolved from anywhere that
isn't the bundled sidecar, a one-time stderr warning fires. The trigger
was a real incident — a developer (Claude) ran a one-off ``python -c``
seed script during PR-B smoke testing without setting ``HIRED_DB_URL``,
which wrote test fixtures into the user's production DB and overwrote
real application data. The warning makes that class of mistake visible
the moment it happens; ``HIRED_PROD_DB_QUIET=1`` suppresses it for
intentional production-path tooling.
"""

from __future__ import annotations

import os
import sqlite3
import sys
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

_prod_db_warning_emitted = False


def _maybe_warn_prod_db() -> None:
    """Emit a one-time stderr warning when an unbundled caller touches the prod DB.

    Inside the PyInstaller bundle (``sys.frozen``) the production path is
    the correct path — no warning. Tests set ``HIRED_DB_URL`` (see
    ``tests/conftest.py``) so they never reach this branch. The branch
    that *does* hit it is the one we care about: a developer running
    ``uv run python -c ...`` or a custom script against the real user DB.

    Set ``HIRED_PROD_DB_QUIET=1`` to suppress when production-path access
    is intentional (e.g. a manual migration helper).
    """
    global _prod_db_warning_emitted
    if _prod_db_warning_emitted:
        return
    if getattr(sys, "frozen", False):
        return
    if os.environ.get("HIRED_PROD_DB_QUIET") == "1":
        return
    _prod_db_warning_emitted = True
    print(
        f"WARNING: opening the production database at {DEFAULT_DB_PATH}.\n"
        "         Set HIRED_DB_URL=sqlite:///./scratch.db for scratch work.\n"
        "         (Suppress this with HIRED_PROD_DB_QUIET=1 when intentional.)",
        file=sys.stderr,
        flush=True,
    )


def resolve_db_url() -> str:
    """Return the configured database URL, creating the default dir if needed."""
    override = os.environ.get("HIRED_DB_URL")
    if override:
        return override
    DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
    _maybe_warn_prod_db()
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
