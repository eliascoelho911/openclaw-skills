"""ORM model for monthly closure snapshots."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from compras_divididas.infrastructure.db.session import Base


class MonthlyClosureModel(Base):
    """Monthly closure persisted snapshot."""

    __tablename__ = "monthly_closure"
    __table_args__ = (
        CheckConstraint(
            "period_month >= 1 AND period_month <= 12",
            name="ck_monthly_closure_month_range",
        ),
        CheckConstraint(
            "participant_a_id <> participant_b_id",
            name="ck_monthly_closure_distinct_participants",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("process_run.id"), unique=True)
    period_year: Mapped[int] = mapped_column(Integer)
    period_month: Mapped[int] = mapped_column(Integer)
    participant_a_id: Mapped[UUID] = mapped_column(ForeignKey("participant.id"))
    participant_b_id: Mapped[UUID] = mapped_column(ForeignKey("participant.id"))
    total_a_cents: Mapped[int] = mapped_column(BigInteger)
    total_b_cents: Mapped[int] = mapped_column(BigInteger)
    net_balance_cents: Mapped[int] = mapped_column(BigInteger)
    payer_id: Mapped[UUID | None] = mapped_column(ForeignKey("participant.id"))
    receiver_id: Mapped[UUID | None] = mapped_column(ForeignKey("participant.id"))
    transfer_amount_cents: Mapped[int] = mapped_column(BigInteger)
    valid_count: Mapped[int] = mapped_column(Integer)
    invalid_count: Mapped[int] = mapped_column(Integer)
    ignored_count: Mapped[int] = mapped_column(Integer)
    deduplicated_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        Enum("finalized", "superseded", name="closure_status")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
