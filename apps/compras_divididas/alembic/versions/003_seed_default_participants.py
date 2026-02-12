"""Seed default active participants.

Revision ID: 003_seed_default_participants
Revises: 002_create_financial_core
Create Date: 2026-02-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_seed_default_participants"
down_revision: str | None = "002_create_financial_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ELIAS_ID = "7f3e0f2c-0f5e-4e5a-9f35-1f5d2e2d3a11"
LETICIA_ID = "2ab1c46d-6d1b-4e97-9af0-3f5f7f0a8b22"


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            INSERT INTO participants (id, code, display_name, is_active)
            SELECT
                '{ELIAS_ID}'::uuid,
                'elias',
                'Elias',
                true
            WHERE NOT EXISTS (SELECT 1 FROM participants)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO participants (id, code, display_name, is_active)
            SELECT
                '{LETICIA_ID}'::uuid,
                'leticia',
                'Letícia',
                true
            WHERE NOT EXISTS (
                SELECT 1
                FROM participants
                WHERE id = '{LETICIA_ID}'::uuid
            )
              AND EXISTS (
                SELECT 1
                FROM participants
                WHERE id = '{ELIAS_ID}'::uuid
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"""
            DELETE FROM participants
            WHERE id IN (
                '{ELIAS_ID}'::uuid,
                '{LETICIA_ID}'::uuid
            )
            """
        )
    )
