"""Phase 5 schema: source-tracked materials, company-brief cache, practice attempts.

Three additions back the application-generation flow:

* ``application_materials`` gains ``source_meta_json`` (citations/URLs the
  brief cites) and ``profile_version`` (so CV-tailoring and cover-letter
  rows fall out of cache when the profile bumps — exactly the same trick
  ``job_scores`` plays for scores). Company-brief rows ignore the version
  column because a company is the same company regardless of who applies.
* ``company_briefs`` caches one research-call result per company. Keyed by
  ``company_lower`` (case-insensitive unique) so apply-to-three-jobs at the
  same company costs one research call, not three.
* ``practice_attempts`` stores per-question practice answers + feedback so
  the interview-prep view can show "you've answered this".

The empty-row defaults assume Phase 5 ships before any production user has
generated materials, so we don't need a backfill plan for ``profile_version``.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-10 00:00:00

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("application_materials") as batch_op:
        batch_op.add_column(sa.Column("source_meta_json", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "profile_version",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )

    op.create_index(
        "ix_application_materials_application_type",
        "application_materials",
        ["application_id", "type"],
    )

    op.create_table(
        "company_briefs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_lower", sa.String(255), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("sources_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_lower", name="uq_company_briefs_company_lower"),
    )

    op.create_table(
        "practice_attempts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "application_id",
            sa.Integer(),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(32), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("feedback_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_index(
        "ix_practice_attempts_application_id",
        "practice_attempts",
        ["application_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_practice_attempts_application_id", table_name="practice_attempts")
    op.drop_table("practice_attempts")
    op.drop_table("company_briefs")
    op.drop_index("ix_application_materials_application_type", table_name="application_materials")
    with op.batch_alter_table("application_materials") as batch_op:
        batch_op.drop_column("profile_version")
        batch_op.drop_column("source_meta_json")
