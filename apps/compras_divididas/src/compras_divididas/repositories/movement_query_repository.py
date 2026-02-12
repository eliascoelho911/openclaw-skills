"""Read-oriented queries for movements and monthly aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from compras_divididas.db.models.financial_movement import (
    FinancialMovement,
    MovementType,
)
from compras_divididas.domain.money import quantize_money


@dataclass(frozen=True, slots=True)
class MovementQueryFilters:
    """Supported query filters for movement search endpoint."""

    competence_month: date
    movement_type: MovementType | None = None
    description: str | None = None
    amount: Decimal | None = None
    participant_id: str | None = None
    external_id: str | None = None
    limit: int = 50
    offset: int = 0


class MovementQueryRepository:
    """Repository focused on read use cases for US2."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_movements(
        self,
        filters: MovementQueryFilters,
    ) -> tuple[list[FinancialMovement], int]:
        statement = self._apply_filters(select(FinancialMovement), filters)

        total_statement = select(func.count()).select_from(statement.subquery())
        total = int(self._session.scalar(total_statement) or 0)

        page_statement = (
            statement.order_by(
                FinancialMovement.occurred_at.desc(),
                FinancialMovement.created_at.desc(),
            )
            .limit(filters.limit)
            .offset(filters.offset)
        )
        items = list(self._session.scalars(page_statement).all())
        return items, total

    def get_monthly_totals(
        self, competence_month: date
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Return gross, refunds and net totals for the month."""

        gross_statement = select(
            func.coalesce(func.sum(FinancialMovement.amount), Decimal("0.00"))
        ).where(
            FinancialMovement.competence_month == competence_month,
            FinancialMovement.movement_type == MovementType.PURCHASE,
        )
        refunds_statement = select(
            func.coalesce(func.sum(FinancialMovement.amount), Decimal("0.00"))
        ).where(
            FinancialMovement.competence_month == competence_month,
            FinancialMovement.movement_type == MovementType.REFUND,
        )

        gross = quantize_money(
            Decimal(self._session.scalar(gross_statement) or Decimal("0"))
        )
        refunds = quantize_money(
            Decimal(self._session.scalar(refunds_statement) or Decimal("0"))
        )
        return gross, refunds, quantize_money(gross - refunds)

    def get_paid_totals_by_participant(
        self, competence_month: date
    ) -> dict[str, Decimal]:
        """Aggregate paid total by participant, subtracting refunds."""

        paid_case = case(
            (
                FinancialMovement.movement_type == MovementType.PURCHASE,
                FinancialMovement.amount,
            ),
            (
                FinancialMovement.movement_type == MovementType.REFUND,
                -FinancialMovement.amount,
            ),
            else_=Decimal("0.00"),
        )

        statement = (
            select(
                FinancialMovement.payer_participant_id,
                func.coalesce(func.sum(paid_case), Decimal("0.00")),
            )
            .where(FinancialMovement.competence_month == competence_month)
            .group_by(FinancialMovement.payer_participant_id)
        )

        rows = self._session.execute(statement).all()
        return {
            str(participant_id): quantize_money(Decimal(total))
            for participant_id, total in rows
        }

    @staticmethod
    def _apply_filters(
        statement: Select[tuple[FinancialMovement]],
        filters: MovementQueryFilters,
    ) -> Select[tuple[FinancialMovement]]:
        typed_statement = statement.where(
            FinancialMovement.competence_month == filters.competence_month
        )

        if filters.movement_type is not None:
            typed_statement = typed_statement.where(
                FinancialMovement.movement_type == filters.movement_type
            )
        if filters.description is not None:
            typed_statement = typed_statement.where(
                FinancialMovement.description.ilike(f"%{filters.description}%")
            )
        if filters.amount is not None:
            typed_statement = typed_statement.where(
                FinancialMovement.amount == quantize_money(filters.amount)
            )
        if filters.participant_id is not None:
            typed_statement = typed_statement.where(
                FinancialMovement.payer_participant_id == filters.participant_id
            )
        if filters.external_id is not None:
            typed_statement = typed_statement.where(
                FinancialMovement.external_id == filters.external_id
            )

        return typed_statement
