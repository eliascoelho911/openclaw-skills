"""Recurrence event ORM model."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from compras_divididas.db.base import Base


class RecurrenceEventType(enum.StrEnum):
    """Functional recurrence event types."""

    RECURRENCE_CREATED = "recurrence_created"
    RECURRENCE_UPDATED = "recurrence_updated"
    RECURRENCE_PAUSED = "recurrence_paused"
    RECURRENCE_REACTIVATED = "recurrence_reactivated"
    RECURRENCE_ENDED = "recurrence_ended"
    RECURRENCE_GENERATED = "recurrence_generated"
    RECURRENCE_BLOCKED = "recurrence_blocked"
    RECURRENCE_FAILED = "recurrence_failed"
    RECURRENCE_IGNORED = "recurrence_ignored"


class RecurrenceEvent(Base):
    """Append-only functional event linked to recurrence lifecycle."""

    __tablename__ = "recurrence_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    recurrence_rule_id: Mapped[UUID] = mapped_column(
        ForeignKey("recurrence_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    recurrence_occurrence_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("recurrence_occurrences.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[RecurrenceEventType] = mapped_column(
        Enum(
            RecurrenceEventType,
            name="recurrence_event_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
    )
    actor_participant_id: Mapped[str | None] = mapped_column(
        ForeignKey("participants.id"),
        nullable=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    recurrence_rule: Mapped[Any] = relationship(
        "RecurrenceRule",
        back_populates="events",
    )
    recurrence_occurrence: Mapped[Any] = relationship(
        "RecurrenceOccurrence",
        back_populates="events",
    )
