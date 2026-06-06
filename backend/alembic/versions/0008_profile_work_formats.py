"""Add work_formats_json column to profile.

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("profile", sa.Column("work_formats_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("profile", "work_formats_json")
