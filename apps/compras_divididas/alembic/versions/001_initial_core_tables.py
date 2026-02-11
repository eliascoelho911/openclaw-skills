"""Create initial core tables for compras-divididas."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial_core_tables"
down_revision = None
branch_labels = None
depends_on = None


source_type_enum = sa.Enum("manual_copy", "whatsapp_export", name="source_type")
process_run_status_enum = sa.Enum(
    "received", "parsed", "reconciled", "failed", name="process_run_status"
)
classification_enum = sa.Enum(
    "valid", "invalid", "ignored", "deduplicated", name="entry_classification"
)
closure_status_enum = sa.Enum("finalized", "superseded", name="closure_status")


def upgrade() -> None:
    """Apply schema upgrades."""
    bind = op.get_bind()
    source_type_enum.create(bind, checkfirst=True)
    process_run_status_enum.create(bind, checkfirst=True)
    classification_enum.create(bind, checkfirst=True)
    closure_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "participant",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_id", name="uq_participant_external_id"),
    )

    op.create_table(
        "process_run",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("input_hash", sa.Text(), nullable=False),
        sa.Column("source_type", source_type_enum, nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("status", process_run_status_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "period_month >= 1 AND period_month <= 12",
            name="ck_process_run_month_range",
        ),
        sa.UniqueConstraint("input_hash", name="uq_process_run_input_hash"),
    )
    op.create_index(
        "ix_process_run_period",
        "process_run",
        ["period_year", "period_month"],
        unique=False,
    )

    op.create_table(
        "raw_message",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_message_id", sa.Text(), nullable=True),
        sa.Column("author_external_id", sa.Text(), nullable=False),
        sa.Column("author_display_name", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "inferred_month", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["process_run.id"], name="fk_raw_message_run_id"
        ),
    )

    op.create_table(
        "extracted_entry",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("normalized_description", sa.Text(), nullable=True),
        sa.Column("amount_cents", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=False, server_default="BRL"),
        sa.Column("classification", classification_enum, nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=True),
        sa.Column("reason_message", sa.Text(), nullable=True),
        sa.Column(
            "is_refund_keyword", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("dedupe_key", sa.Text(), nullable=True),
        sa.Column("dedupe_bucket_5m", sa.BigInteger(), nullable=True),
        sa.Column("included_in_calculation", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["participant.id"],
            name="fk_extracted_entry_participant_id",
        ),
        sa.ForeignKeyConstraint(
            ["raw_message_id"],
            ["raw_message.id"],
            name="fk_extracted_entry_raw_message_id",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["process_run.id"], name="fk_extracted_entry_run_id"
        ),
        sa.CheckConstraint(
            "classification != 'valid' OR amount_cents IS NOT NULL",
            name="ck_extracted_entry_valid_amount",
        ),
    )
    op.create_index(
        "ix_extracted_entry_author_dedupe_bucket",
        "extracted_entry",
        ["dedupe_key", "dedupe_bucket_5m"],
        unique=False,
    )
    op.create_index(
        "ix_extracted_entry_classification",
        "extracted_entry",
        ["classification"],
        unique=False,
    )

    op.create_table(
        "monthly_closure",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("participant_a_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_b_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_a_cents", sa.BigInteger(), nullable=False),
        sa.Column("total_b_cents", sa.BigInteger(), nullable=False),
        sa.Column("net_balance_cents", sa.BigInteger(), nullable=False),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("receiver_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transfer_amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("valid_count", sa.Integer(), nullable=False),
        sa.Column("invalid_count", sa.Integer(), nullable=False),
        sa.Column("ignored_count", sa.Integer(), nullable=False),
        sa.Column("deduplicated_count", sa.Integer(), nullable=False),
        sa.Column("status", closure_status_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "period_month >= 1 AND period_month <= 12",
            name="ck_monthly_closure_month_range",
        ),
        sa.CheckConstraint(
            "participant_a_id <> participant_b_id",
            name="ck_monthly_closure_distinct_participants",
        ),
        sa.ForeignKeyConstraint(
            ["participant_a_id"],
            ["participant.id"],
            name="fk_monthly_closure_participant_a_id",
        ),
        sa.ForeignKeyConstraint(
            ["participant_b_id"],
            ["participant.id"],
            name="fk_monthly_closure_participant_b_id",
        ),
        sa.ForeignKeyConstraint(
            ["payer_id"], ["participant.id"], name="fk_monthly_closure_payer_id"
        ),
        sa.ForeignKeyConstraint(
            ["receiver_id"], ["participant.id"], name="fk_monthly_closure_receiver_id"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["process_run.id"], name="fk_monthly_closure_run_id"
        ),
        sa.UniqueConstraint("run_id", name="uq_monthly_closure_run_id"),
    )
    op.create_index(
        "ix_monthly_closure_period",
        "monthly_closure",
        ["period_year", "period_month"],
        unique=False,
    )

    op.create_table(
        "closure_line_item",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("closure_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["closure_id"],
            ["monthly_closure.id"],
            name="fk_closure_line_item_closure_id",
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["extracted_entry.id"], name="fk_closure_line_item_entry_id"
        ),
        sa.UniqueConstraint(
            "closure_id", "entry_id", name="uq_closure_line_item_closure_entry"
        ),
    )


def downgrade() -> None:
    """Revert schema upgrades."""
    op.drop_table("closure_line_item")
    op.drop_index("ix_monthly_closure_period", table_name="monthly_closure")
    op.drop_table("monthly_closure")
    op.drop_index("ix_extracted_entry_classification", table_name="extracted_entry")
    op.drop_index(
        "ix_extracted_entry_author_dedupe_bucket", table_name="extracted_entry"
    )
    op.drop_table("extracted_entry")
    op.drop_table("raw_message")
    op.drop_index("ix_process_run_period", table_name="process_run")
    op.drop_table("process_run")
    op.drop_table("participant")

    bind = op.get_bind()
    closure_status_enum.drop(bind, checkfirst=True)
    classification_enum.drop(bind, checkfirst=True)
    process_run_status_enum.drop(bind, checkfirst=True)
    source_type_enum.drop(bind, checkfirst=True)
