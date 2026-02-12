"""Add recurrence rule, occurrence and event tables.

Revision ID: 20260211_01_add_recurrence_tables
Revises: 003_seed_default_participants
Create Date: 2026-02-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260211_01_add_recurrence_tables"
down_revision: str | None = "003_seed_default_participants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


recurrence_periodicity_enum = sa.Enum("monthly", name="recurrence_periodicity")
recurrence_status_enum = sa.Enum("active", "paused", "ended", name="recurrence_status")
recurrence_occurrence_status_enum = sa.Enum(
    "pending",
    "generated",
    "blocked",
    "failed",
    name="recurrence_occurrence_status",
)
recurrence_event_type_enum = sa.Enum(
    "recurrence_created",
    "recurrence_updated",
    "recurrence_paused",
    "recurrence_reactivated",
    "recurrence_ended",
    "recurrence_generated",
    "recurrence_blocked",
    "recurrence_failed",
    "recurrence_ignored",
    name="recurrence_event_type",
)


def upgrade() -> None:
    op.create_table(
        "recurrence_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(length=280), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payer_participant_id", sa.String(length=32), nullable=False),
        sa.Column(
            "requested_by_participant_id",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "split_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("periodicity", recurrence_periodicity_enum, nullable=False),
        sa.Column("reference_day", sa.SmallInteger(), nullable=False),
        sa.Column("start_competence_month", sa.Date(), nullable=False),
        sa.Column("end_competence_month", sa.Date(), nullable=True),
        sa.Column("status", recurrence_status_enum, nullable=False),
        sa.Column("first_generated_competence_month", sa.Date(), nullable=True),
        sa.Column("last_generated_competence_month", sa.Date(), nullable=True),
        sa.Column("next_competence_month", sa.Date(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
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
        sa.CheckConstraint("amount > 0", name="ck_recurrence_rules_amount_positive"),
        sa.CheckConstraint(
            "reference_day BETWEEN 1 AND 31",
            name="ck_recurrence_rules_reference_day_range",
        ),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM start_competence_month) = 1",
            name="ck_recurrence_rules_start_is_month_start",
        ),
        sa.CheckConstraint(
            "next_competence_month IS NULL "
            "OR EXTRACT(DAY FROM next_competence_month) = 1",
            name="ck_recurrence_rules_next_is_month_start",
        ),
        sa.CheckConstraint(
            "first_generated_competence_month IS NULL "
            "OR EXTRACT(DAY FROM first_generated_competence_month) = 1",
            name="ck_recurrence_rules_first_generated_is_month_start",
        ),
        sa.CheckConstraint(
            "last_generated_competence_month IS NULL "
            "OR EXTRACT(DAY FROM last_generated_competence_month) = 1",
            name="ck_recurrence_rules_last_generated_is_month_start",
        ),
        sa.CheckConstraint(
            "end_competence_month IS NULL OR "
            "(EXTRACT(DAY FROM end_competence_month) = 1 "
            "AND end_competence_month >= start_competence_month)",
            name="ck_recurrence_rules_end_competence_month_valid",
        ),
        sa.CheckConstraint("version > 0", name="ck_recurrence_rules_version_positive"),
        sa.ForeignKeyConstraint(
            ["payer_participant_id"],
            ["participants.id"],
            name="fk_recurrence_rules_payer_participant_id",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_participant_id"],
            ["participants.id"],
            name="fk_recurrence_rules_requested_by_participant_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_recurrence_rules_status_next_competence_month",
        "recurrence_rules",
        ["status", "next_competence_month"],
        unique=False,
    )

    op.create_table(
        "recurrence_occurrences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recurrence_rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("competence_month", sa.Date(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("status", recurrence_occurrence_status_enum, nullable=False),
        sa.Column("movement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("blocked_reason_code", sa.String(length=64), nullable=True),
        sa.Column("blocked_reason_message", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "EXTRACT(DAY FROM competence_month) = 1",
            name="ck_recurrence_occurrences_competence_is_month_start",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_recurrence_occurrences_attempt_count_non_negative",
        ),
        sa.CheckConstraint(
            "(status != 'generated' AND movement_id IS NULL) "
            "OR (status = 'generated' AND movement_id IS NOT NULL)",
            name="ck_recurrence_occurrences_generated_requires_movement",
        ),
        sa.CheckConstraint(
            "(status != 'blocked') OR "
            "(blocked_reason_code IS NOT NULL AND blocked_reason_message IS NOT NULL)",
            name="ck_recurrence_occurrences_blocked_requires_reason",
        ),
        sa.ForeignKeyConstraint(
            ["recurrence_rule_id"],
            ["recurrence_rules.id"],
            ondelete="CASCADE",
            name="fk_recurrence_occurrences_rule_id",
        ),
        sa.ForeignKeyConstraint(
            ["movement_id"],
            ["financial_movements.id"],
            name="fk_recurrence_occurrences_movement_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "uq_recurrence_occurrences_rule_competence",
        "recurrence_occurrences",
        ["recurrence_rule_id", "competence_month"],
        unique=True,
    )
    op.create_index(
        "uq_recurrence_occurrences_movement_id",
        "recurrence_occurrences",
        ["movement_id"],
        unique=True,
        postgresql_where=sa.text("movement_id IS NOT NULL"),
    )
    op.create_index(
        "ix_recurrence_occurrences_competence_status",
        "recurrence_occurrences",
        ["competence_month", "status"],
        unique=False,
    )

    op.create_table(
        "recurrence_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recurrence_rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "recurrence_occurrence_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("event_type", recurrence_event_type_enum, nullable=False),
        sa.Column("actor_participant_id", sa.String(length=32), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["recurrence_rule_id"],
            ["recurrence_rules.id"],
            ondelete="CASCADE",
            name="fk_recurrence_events_rule_id",
        ),
        sa.ForeignKeyConstraint(
            ["recurrence_occurrence_id"],
            ["recurrence_occurrences.id"],
            ondelete="SET NULL",
            name="fk_recurrence_events_occurrence_id",
        ),
        sa.ForeignKeyConstraint(
            ["actor_participant_id"],
            ["participants.id"],
            name="fk_recurrence_events_actor_participant_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_recurrence_events_rule_created_at",
        "recurrence_events",
        ["recurrence_rule_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_recurrence_events_rule_created_at", table_name="recurrence_events"
    )
    op.drop_table("recurrence_events")

    op.drop_index(
        "ix_recurrence_occurrences_competence_status",
        table_name="recurrence_occurrences",
    )
    op.drop_index(
        "uq_recurrence_occurrences_movement_id",
        table_name="recurrence_occurrences",
    )
    op.drop_index(
        "uq_recurrence_occurrences_rule_competence",
        table_name="recurrence_occurrences",
    )
    op.drop_table("recurrence_occurrences")

    op.drop_index(
        "ix_recurrence_rules_status_next_competence_month",
        table_name="recurrence_rules",
    )
    op.drop_table("recurrence_rules")

    recurrence_event_type_enum.drop(op.get_bind(), checkfirst=True)
    recurrence_occurrence_status_enum.drop(op.get_bind(), checkfirst=True)
    recurrence_status_enum.drop(op.get_bind(), checkfirst=True)
    recurrence_periodicity_enum.drop(op.get_bind(), checkfirst=True)
