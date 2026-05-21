"""Tests for the prod-DB-write guard added in v0.3.1.

The default ``~/.hired/data.db`` path is the correct path for the bundled
sidecar but a footgun for one-off ``uv run python -c "..."`` smoke scripts.
A real Phase 8 PR-B incident overwrote real user data this way; the
warning makes that mistake visible the moment it happens.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# The conftest autouse fixture sets HIRED_DB_URL on every test. These
# tests need to bypass that to exercise the default-path branch.


def _reset_warning_flag() -> None:
    """Force the next call to ``_maybe_warn_prod_db`` to be 'first'."""
    import db.session

    db.session._prod_db_warning_emitted = False


def test_warning_fires_on_default_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("HIRED_DB_URL", raising=False)
    monkeypatch.delenv("HIRED_PROD_DB_QUIET", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    # Reroute the "production" path away from the real ~/.hired so the
    # test never touches it. Resolve still triggers the warning because
    # the default path is what's being opened — what we want.
    fake_dir = tmp_path / ".hired"
    monkeypatch.setattr("db.session.DEFAULT_DB_DIR", fake_dir)
    monkeypatch.setattr("db.session.DEFAULT_DB_PATH", fake_dir / "data.db")
    _reset_warning_flag()

    import db.session

    url = db.session.resolve_db_url()
    assert url == f"sqlite:///{fake_dir / 'data.db'}"
    err = capsys.readouterr().err
    assert "production database" in err
    assert "HIRED_DB_URL" in err


def test_warning_silent_when_override_is_set(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HIRED_DB_URL", "sqlite:///./scratch.db")
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    _reset_warning_flag()

    import db.session

    db.session.resolve_db_url()
    assert capsys.readouterr().err == ""


def test_warning_silent_in_pyinstaller_bundle(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """The bundled sidecar IS the legitimate production path. Stay quiet."""
    monkeypatch.delenv("HIRED_DB_URL", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr("db.session.DEFAULT_DB_DIR", tmp_path / ".hired")
    monkeypatch.setattr("db.session.DEFAULT_DB_PATH", tmp_path / ".hired" / "data.db")
    _reset_warning_flag()

    import db.session

    db.session.resolve_db_url()
    assert capsys.readouterr().err == ""


def test_warning_silent_when_quiet_env_is_set(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("HIRED_DB_URL", raising=False)
    monkeypatch.setenv("HIRED_PROD_DB_QUIET", "1")
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr("db.session.DEFAULT_DB_DIR", tmp_path / ".hired")
    monkeypatch.setattr("db.session.DEFAULT_DB_PATH", tmp_path / ".hired" / "data.db")
    _reset_warning_flag()

    import db.session

    db.session.resolve_db_url()
    assert capsys.readouterr().err == ""


def test_warning_only_fires_once(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("HIRED_DB_URL", raising=False)
    monkeypatch.delenv("HIRED_PROD_DB_QUIET", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr("db.session.DEFAULT_DB_DIR", tmp_path / ".hired")
    monkeypatch.setattr("db.session.DEFAULT_DB_PATH", tmp_path / ".hired" / "data.db")
    _reset_warning_flag()

    import db.session

    db.session.resolve_db_url()
    first_err = capsys.readouterr().err
    db.session.resolve_db_url()
    second_err = capsys.readouterr().err

    assert "production database" in first_err
    assert second_err == ""  # quiet on every subsequent call
