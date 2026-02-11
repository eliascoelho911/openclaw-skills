"""Create participants and financial movements core tables.

Revision ID: 002_create_financial_core
Revises:
Create Date: 2026-02-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_create_financial_core"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


movement_type_enum = sa.Enum("purchase", "refund", name="movement_type")


def upgrade() -> None:
    op.create_table(
        "participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_participants_code"),
    )

    op.create_table(
        "financial_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_type", movement_type_enum, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.String(length=280), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("competence_month", sa.Date(), nullable=False),
        sa.Column(
            "payer_participant_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "requested_by_participant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=120), nullable=True),
        sa.Column("original_purchase_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("amount > 0", name="ck_financial_movements_amount_positive"),
        sa.CheckConstraint(
            """
            (movement_type = 'purchase' AND original_purchase_id IS NULL)
            OR
            (movement_type = 'refund' AND original_purchase_id IS NOT NULL)
            """,
            name="ck_financial_movements_refund_requires_original",
        ),
        sa.ForeignKeyConstraint(
            ["payer_participant_id"],
            ["participants.id"],
            name="fk_financial_movements_payer_participant_id",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_participant_id"],
            ["participants.id"],
            name="fk_financial_movements_requested_by_participant_id",
        ),
        sa.ForeignKeyConstraint(
            ["original_purchase_id"],
            ["financial_movements.id"],
            name="fk_financial_movements_original_purchase_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_financial_movements_competence_month",
        "financial_movements",
        ["competence_month"],
        unique=False,
    )

    op.create_index(
        "uq_financial_movements_competence_payer_external_id",
        "financial_movements",
        ["competence_month", "payer_participant_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_financial_movements_competence_payer_external_id",
        table_name="financial_movements",
    )
    op.drop_index(
        "ix_financial_movements_competence_month",
        table_name="financial_movements",
    )
    op.drop_table("financial_movements")
    op.drop_table("participants")
    movement_type_enum.drop(op.get_bind(), checkfirst=True)
