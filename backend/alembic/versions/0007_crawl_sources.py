"""Add crawl_sources table and source_interval_hours app_config key.

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-26
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crawl_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("company_slug", sa.String(255), nullable=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
    )
    # Seed the global scheduler interval (hours) into app_config.
    op.execute(
        "INSERT OR IGNORE INTO app_config (key, value) VALUES ('source_interval_hours', '24')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM app_config WHERE key = 'source_interval_hours'")
    op.drop_table("crawl_sources")
