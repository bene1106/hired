"""Mock-interview runs: timed-runner attempts with transcripts.

Adds ``mock_interview_runs`` — one row per timed mock-interview attempt against
an ``interviews`` row. M2 fills ``transcript_json``; ``evaluation_json`` and
``voice_mode`` are added now (nullable/defaulted) so the M3 scoring and M4 voice
milestones need no further migration.

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-24 00:00:01

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mock_interview_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "interview_id",
            sa.Integer(),
            sa.ForeignKey("interviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="in_progress"),
        sa.Column("voice_mode", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("transcript_json", sa.JSON(), nullable=True),
        sa.Column("evaluation_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_mock_interview_runs_interview_id",
        "mock_interview_runs",
        ["interview_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_mock_interview_runs_interview_id", table_name="mock_interview_runs")
    op.drop_table("mock_interview_runs")
