"""Phase 4 schema: richer jobs columns + profile_version for cache invalidation.

Adds the four normalized job columns the spec requires (remote policy,
salary band, currency) so the crawler can persist what it scrapes without
losing structure.

Adds an integer ``profile_version`` to ``profile`` (bumped on every profile
update or CV re-upload) and mirrors it on ``job_scores``. The scoring cache
keys on ``(profile_version, job_id)`` — when the user edits their profile,
the version bumps and stale scores fall out of cache automatically.

Tables are still empty in pre-Phase-4 installs, so the new NOT NULL column
on ``profile_version`` defaults to ``0`` server-side without a backfill.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-09 00:00:00

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.add_column(sa.Column("remote_policy", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("salary_min", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("salary_max", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("currency", sa.String(8), nullable=True))

    with op.batch_alter_table("profile") as batch_op:
        batch_op.add_column(
            sa.Column(
                "profile_version",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )

    with op.batch_alter_table("job_scores") as batch_op:
        batch_op.add_column(
            sa.Column(
                "profile_version",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )

    op.create_index("ix_job_scores_job_id", "job_scores", ["job_id"])
    op.create_index(
        "ix_job_scores_profile_version_job_id",
        "job_scores",
        ["profile_version", "job_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_scores_profile_version_job_id", table_name="job_scores")
    op.drop_index("ix_job_scores_job_id", table_name="job_scores")

    with op.batch_alter_table("job_scores") as batch_op:
        batch_op.drop_column("profile_version")

    with op.batch_alter_table("profile") as batch_op:
        batch_op.drop_column("profile_version")

    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_column("currency")
        batch_op.drop_column("salary_max")
        batch_op.drop_column("salary_min")
        batch_op.drop_column("remote_policy")
