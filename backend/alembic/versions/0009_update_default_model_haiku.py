"""Update default model from Opus to Haiku.

Existing installs that never changed the model keep Claude Opus as their
active model — the migration only changes the seeded default for fresh
installs and reverts the value for anyone still on the old default.

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-08 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

OLD_MODEL = "claude-opus-4-7"
NEW_MODEL = "claude-haiku-4-5-20251001"


def upgrade() -> None:
    op.execute(
        f"UPDATE app_config SET value = '{NEW_MODEL}' WHERE key = 'model' AND value = '{OLD_MODEL}'"
    )


def downgrade() -> None:
    op.execute(
        f"UPDATE app_config SET value = '{OLD_MODEL}' WHERE key = 'model' AND value = '{NEW_MODEL}'"
    )
