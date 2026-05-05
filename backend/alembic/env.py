"""Alembic environment.

We override ``sqlalchemy.url`` from ``db.session.resolve_db_url()`` so that
the ``HIRED_DB_URL`` env var works for tests and tooling without needing to
edit alembic.ini.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

# When `alembic` is invoked as a CLI subprocess, its cwd may be elsewhere and
# `backend/` is not on sys.path. Pytest and uvicorn add it for us; for the CLI
# we add it explicitly so `from db.models import Base` resolves.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import engine_from_config, pool  # noqa: E402

from alembic import context  # noqa: E402
from db.models import Base  # noqa: E402
from db.session import resolve_db_url  # noqa: E402

config = context.config
config.set_main_option("sqlalchemy.url", resolve_db_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # required for SQLite ALTER TABLE in later phases
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
