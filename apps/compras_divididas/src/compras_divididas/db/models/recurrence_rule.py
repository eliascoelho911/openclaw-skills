"""Recurrence rule ORM model."""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from compras_divididas.db.base import Base


class RecurrencePeriodicity(enum.StrEnum):
    """Supported recurrence periodicity values."""

    MONTHLY = "monthly"


class RecurrenceStatus(enum.StrEnum):
    """Recurrence lifecycle states."""

    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


class RecurrenceRule(Base):
    """Represents a recurring transaction rule."""

    __tablename__ = "recurrence_rules"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_recurrence_rules_amount_positive"),
        CheckConstraint(
            "reference_day BETWEEN 1 AND 31",
            name="ck_recurrence_rules_reference_day_range",
        ),
        CheckConstraint(
            "end_competence_month IS NULL OR "
            "end_competence_month >= start_competence_month",
            name="ck_recurrence_rules_end_competence_month_valid",
        ),
        CheckConstraint("version > 0", name="ck_recurrence_rules_version_positive"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    description: Mapped[str] = mapped_column(String(280), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payer_participant_id: Mapped[str] = mapped_column(
        ForeignKey("participants.id"),
        nullable=False,
    )
    requested_by_participant_id: Mapped[str] = mapped_column(
        ForeignKey("participants.id"),
        nullable=False,
    )
    split_config: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    periodicity: Mapped[RecurrencePeriodicity] = mapped_column(
        Enum(
            RecurrencePeriodicity,
            name="recurrence_periodicity",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
    )
    reference_day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_competence_month: Mapped[date] = mapped_column(Date, nullable=False)
    end_competence_month: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[RecurrenceStatus] = mapped_column(
        Enum(
            RecurrenceStatus,
            name="recurrence_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
    )
    first_generated_competence_month: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    last_generated_competence_month: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    next_competence_month: Mapped[date] = mapped_column(Date, nullable=False)
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    occurrences: Mapped[list[Any]] = relationship(
        "RecurrenceOccurrence",
        back_populates="recurrence_rule",
        cascade="all, delete-orphan",
    )
    events: Mapped[list[Any]] = relationship(
        "RecurrenceEvent",
        back_populates="recurrence_rule",
        cascade="all, delete-orphan",
    )
