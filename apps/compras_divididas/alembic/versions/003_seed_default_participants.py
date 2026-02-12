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

ELIAS_ID = "elias"
LETICIA_ID = "leticia"


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            INSERT INTO participants (id, display_name, is_active)
            SELECT
                '{ELIAS_ID}',
                'Elias',
                true
            WHERE NOT EXISTS (SELECT 1 FROM participants)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO participants (id, display_name, is_active)
            SELECT
                '{LETICIA_ID}',
                'Letícia',
                true
            WHERE NOT EXISTS (
                SELECT 1
                FROM participants
                WHERE id = '{LETICIA_ID}'
            )
              AND EXISTS (
                SELECT 1
                FROM participants
                WHERE id = '{ELIAS_ID}'
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
                '{ELIAS_ID}',
                '{LETICIA_ID}'
            )
            """
        )
    )
