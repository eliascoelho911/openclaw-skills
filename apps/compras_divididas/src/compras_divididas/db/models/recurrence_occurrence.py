"""Recurrence occurrence ORM model."""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from compras_divididas.db.base import Base


class RecurrenceOccurrenceStatus(enum.StrEnum):
    """Recurrence occurrence processing states."""

    PENDING = "pending"
    GENERATED = "generated"
    BLOCKED = "blocked"
    FAILED = "failed"


class RecurrenceOccurrence(Base):
    """Represents one recurrence processing result for a competence month."""

    __tablename__ = "recurrence_occurrences"
    __table_args__ = (
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_recurrence_occurrences_attempt_count_non_negative",
        ),
        CheckConstraint(
            "(status != 'generated' AND movement_id IS NULL) "
            "OR (status = 'generated' AND movement_id IS NOT NULL)",
            name="ck_recurrence_occurrences_generated_requires_movement",
        ),
        CheckConstraint(
            "(status != 'blocked') OR "
            "(blocked_reason_code IS NOT NULL AND blocked_reason_message IS NOT NULL)",
            name="ck_recurrence_occurrences_blocked_requires_reason",
        ),
        Index(
            "uq_recurrence_occurrences_rule_competence",
            "recurrence_rule_id",
            "competence_month",
            unique=True,
        ),
        Index(
            "uq_recurrence_occurrences_movement_id",
            "movement_id",
            unique=True,
            postgresql_where=text("movement_id IS NOT NULL"),
        ),
        Index(
            "ix_recurrence_occurrences_competence_status",
            "competence_month",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    recurrence_rule_id: Mapped[UUID] = mapped_column(
        ForeignKey("recurrence_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    competence_month: Mapped[date] = mapped_column(Date, nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[RecurrenceOccurrenceStatus] = mapped_column(
        Enum(
            RecurrenceOccurrenceStatus,
            name="recurrence_occurrence_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
    )
    movement_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("financial_movements.id"),
        nullable=True,
    )
    blocked_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    blocked_reason_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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

    recurrence_rule: Mapped[Any] = relationship(
        "RecurrenceRule",
        back_populates="occurrences",
    )
    events: Mapped[list[Any]] = relationship(
        "RecurrenceEvent",
        back_populates="recurrence_occurrence",
    )
