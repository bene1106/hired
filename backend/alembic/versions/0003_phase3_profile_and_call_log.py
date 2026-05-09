"""Phase 3 schema: plural profile fields + provider_call_log table.

Drops the singular ``target_role`` and ``target_location`` columns and adds
JSON-typed ``target_roles_json``, ``target_locations_json``, and
``priorities_json``. Tables are still empty in pre-Phase-3 installs, so the
column drop is safe (no data to migrate).

Adds the ``provider_call_log`` table that the Settings UI reads to render
per-provider latency and call counts.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-06 00:00:00

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("profile") as batch_op:
        batch_op.drop_column("target_role")
        batch_op.drop_column("target_location")
        batch_op.add_column(sa.Column("target_roles_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("target_locations_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("priorities_json", sa.JSON(), nullable=True))

    op.create_table(
        "provider_call_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("method", sa.String(64), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_provider_call_log_created_at",
        "provider_call_log",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_provider_call_log_created_at", table_name="provider_call_log")
    op.drop_table("provider_call_log")

    with op.batch_alter_table("profile") as batch_op:
        batch_op.drop_column("priorities_json")
        batch_op.drop_column("target_locations_json")
        batch_op.drop_column("target_roles_json")
        batch_op.add_column(sa.Column("target_role", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("target_location", sa.String(255), nullable=True))
