"""Financial movement append-only ORM model."""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from compras_divididas.db.base import Base


class MovementType(enum.StrEnum):
    """Supported movement types."""

    PURCHASE = "purchase"
    REFUND = "refund"


class FinancialMovement(Base):
    """Append-only financial movement for purchases and refunds."""

    __tablename__ = "financial_movements"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_financial_movements_amount_positive"),
        CheckConstraint(
            """
            (movement_type = 'purchase' AND original_purchase_id IS NULL)
            OR
            (movement_type = 'refund' AND original_purchase_id IS NOT NULL)
            """,
            name="ck_financial_movements_refund_requires_original",
        ),
        Index(
            "ix_financial_movements_competence_month",
            "competence_month",
        ),
        Index(
            "uq_financial_movements_competence_payer_external_id",
            "competence_month",
            "payer_participant_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    movement_type: Mapped[MovementType] = mapped_column(
        Enum(
            MovementType,
            name="movement_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(280), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    competence_month: Mapped[date] = mapped_column(Date, nullable=False)
    payer_participant_id: Mapped[str] = mapped_column(
        ForeignKey("participants.id"),
        nullable=False,
    )
    requested_by_participant_id: Mapped[str] = mapped_column(
        ForeignKey("participants.id"),
        nullable=False,
    )
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    original_purchase_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("financial_movements.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    original_purchase: Mapped[FinancialMovement | None] = relationship(
        "FinancialMovement",
        remote_side="FinancialMovement.id",
        foreign_keys=[original_purchase_id],
    )
