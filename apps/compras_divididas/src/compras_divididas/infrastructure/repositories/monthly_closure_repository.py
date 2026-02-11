"""Repository adapter for monthly closure persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from compras_divididas.infrastructure.db.models.monthly_closure import (
    MonthlyClosureModel,
)


@dataclass(frozen=True, slots=True)
class MonthlyClosureCreate:
    """Input data for creating a monthly closure row."""

    id: UUID
    run_id: UUID
    period_year: int
    period_month: int
    participant_a_id: UUID
    participant_b_id: UUID
    total_a_cents: int
    total_b_cents: int
    net_balance_cents: int
    payer_id: UUID | None
    receiver_id: UUID | None
    transfer_amount_cents: int
    valid_count: int
    invalid_count: int
    ignored_count: int
    deduplicated_count: int
    status: str
    created_at: datetime


class MonthlyClosureRepository:
    """SQLAlchemy repository for monthly closure snapshots."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, payload: MonthlyClosureCreate) -> MonthlyClosureModel:
        """Insert a monthly closure and flush session state."""
        row = MonthlyClosureModel(
            id=payload.id,
            run_id=payload.run_id,
            period_year=payload.period_year,
            period_month=payload.period_month,
            participant_a_id=payload.participant_a_id,
            participant_b_id=payload.participant_b_id,
            total_a_cents=payload.total_a_cents,
            total_b_cents=payload.total_b_cents,
            net_balance_cents=payload.net_balance_cents,
            payer_id=payload.payer_id,
            receiver_id=payload.receiver_id,
            transfer_amount_cents=payload.transfer_amount_cents,
            valid_count=payload.valid_count,
            invalid_count=payload.invalid_count,
            ignored_count=payload.ignored_count,
            deduplicated_count=payload.deduplicated_count,
            status=payload.status,
            created_at=payload.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def get_by_id(self, closure_id: UUID) -> MonthlyClosureModel | None:
        """Fetch a monthly closure by id."""
        return self._session.get(MonthlyClosureModel, closure_id)
