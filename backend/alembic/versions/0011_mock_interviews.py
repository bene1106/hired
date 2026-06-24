"""Mock-interview schema: per-application interviews with prepared questions.

Adds the ``interviews`` table — one application has many interviews (round 1,
2, …), each with its type, duration, interviewer gender, optional schedule, and
a cached ``questions_json`` set prepared ahead of a mock run. The
``mock_interview_runs`` table (transcripts + evaluations) lands in a later
milestone, not here.

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-24 00:00:00

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interviews",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "application_id",
            sa.Integer(),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("interview_type", sa.String(32), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "interviewer_gender",
            sa.String(16),
            nullable=False,
            server_default="unspecified",
        ),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("questions_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_interviews_application_id", "interviews", ["application_id"])


def downgrade() -> None:
    op.drop_index("ix_interviews_application_id", table_name="interviews")
    op.drop_table("interviews")
