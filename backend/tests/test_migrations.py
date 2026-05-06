"""Verify the initial migration creates the 7 tables and seeds app_config."""

from __future__ import annotations

from sqlalchemy import inspect, select

from db.migrations import run_migrations
from db.models import AppConfig
from db.session import get_engine, get_session

EXPECTED_TABLES = {
    "profile",
    "jobs",
    "job_scores",
    "applications",
    "application_materials",
    "interview_sessions",
    "app_config",
    "provider_call_log",
}


def test_initial_migration_creates_all_tables_and_seeds_provider() -> None:
    run_migrations()

    inspector = inspect(get_engine())
    tables = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(tables), f"missing tables: {EXPECTED_TABLES - tables}"

    with get_session() as session:
        provider = session.execute(
            select(AppConfig.value).where(AppConfig.key == "provider")
        ).scalar_one()
        model = session.execute(
            select(AppConfig.value).where(AppConfig.key == "model")
        ).scalar_one()
    assert provider == "mock"
    assert model == "claude-opus-4-7"


def test_run_migrations_is_idempotent() -> None:
    run_migrations()
    run_migrations()  # second call should be a no-op, not raise

    inspector = inspect(get_engine())
    assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))


def test_phase3_profile_columns_are_plural() -> None:
    """Phase 3 dropped the singular target_role/target_location in favor of JSON cols."""
    run_migrations()

    inspector = inspect(get_engine())
    cols = {c["name"] for c in inspector.get_columns("profile")}
    assert "target_role" not in cols
    assert "target_location" not in cols
    assert {"target_roles_json", "target_locations_json", "priorities_json"}.issubset(cols)
