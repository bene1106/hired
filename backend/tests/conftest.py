"""Pytest fixtures shared across the backend test suite."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from db.session import reset_engine


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Point the backend at a per-test SQLite file so we never touch ~/.hired/."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("HIRED_DB_URL", f"sqlite:///{db_file}")
    reset_engine()
    yield
    reset_engine()
