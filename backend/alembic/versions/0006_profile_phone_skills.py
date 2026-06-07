"""Add phone and skills_json to profile table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-26
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("profile", sa.Column("phone", sa.String(64), nullable=True))
    op.add_column("profile", sa.Column("skills_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("profile", "skills_json")
    op.drop_column("profile", "phone")
