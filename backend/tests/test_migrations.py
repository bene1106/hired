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
    assert provider == "mock"


def test_run_migrations_is_idempotent() -> None:
    run_migrations()
    run_migrations()  # second call should be a no-op, not raise

    inspector = inspect(get_engine())
    assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))
