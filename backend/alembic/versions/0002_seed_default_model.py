"""Seed the default LLM model in app_config.

The `app_config` table is a key/value store. Phase 2 introduces a `model`
key alongside the existing `provider` key so users can pick a non-default
Anthropic model without code changes.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-06 00:00:00

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

DEFAULT_MODEL = "claude-opus-4-7"


def upgrade() -> None:
    op.bulk_insert(
        sa.table(
            "app_config",
            sa.column("key", sa.String),
            sa.column("value", sa.Text),
        ),
        [{"key": "model", "value": DEFAULT_MODEL}],
    )


def downgrade() -> None:
    op.execute("DELETE FROM app_config WHERE key = 'model'")
