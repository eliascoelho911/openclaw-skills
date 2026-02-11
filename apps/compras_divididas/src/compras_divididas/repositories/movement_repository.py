"""Financial movement persistence operations."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from compras_divididas.db.models.financial_movement import (
    FinancialMovement,
    MovementType,
)


class MovementRepository:
    """Repository for append-only movement persistence and lookup."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def has_duplicate_external_id(
        self,
        *,
        competence_month: date,
        payer_participant_id: UUID,
        external_id: str,
    ) -> bool:
        statement = select(FinancialMovement.id).where(
            FinancialMovement.competence_month == competence_month,
            FinancialMovement.payer_participant_id == payer_participant_id,
            FinancialMovement.external_id == external_id,
        )
        return self._session.scalar(statement) is not None

    def get_purchase_for_update(self, purchase_id: UUID) -> FinancialMovement | None:
        statement = (
            select(FinancialMovement)
            .where(
                FinancialMovement.id == purchase_id,
                FinancialMovement.movement_type == MovementType.PURCHASE,
            )
            .with_for_update()
        )
        return self._session.scalar(statement)

    def get_purchase_by_external_id_for_update(
        self,
        *,
        competence_month: date,
        payer_participant_id: UUID,
        external_id: str,
    ) -> FinancialMovement | None:
        statement = (
            select(FinancialMovement)
            .where(
                FinancialMovement.movement_type == MovementType.PURCHASE,
                FinancialMovement.competence_month == competence_month,
                FinancialMovement.payer_participant_id == payer_participant_id,
                FinancialMovement.external_id == external_id,
            )
            .with_for_update()
        )
        return self._session.scalar(statement)

    def get_total_refunded_amount(self, original_purchase_id: UUID) -> Decimal:
        statement = select(
            func.coalesce(func.sum(FinancialMovement.amount), Decimal("0.00"))
        ).where(
            FinancialMovement.movement_type == MovementType.REFUND,
            FinancialMovement.original_purchase_id == original_purchase_id,
        )
        refunded_amount = self._session.scalar(statement)
        if refunded_amount is None:
            return Decimal("0.00")
        return Decimal(refunded_amount)

    def add(self, movement: FinancialMovement) -> FinancialMovement:
        self._session.add(movement)
        self._session.flush()
        return movement
