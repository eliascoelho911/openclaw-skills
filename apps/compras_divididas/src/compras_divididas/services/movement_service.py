"""Business service for movement registration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from compras_divididas.db.models.financial_movement import (
    FinancialMovement,
    MovementType,
)
from compras_divididas.db.models.participant import Participant
from compras_divididas.domain.competence import competence_month, resolve_occurred_at
from compras_divididas.domain.errors import (
    DuplicateExternalIDError,
    InvalidRequestError,
    PurchaseNotFoundError,
    RefundLimitExceededError,
    compose_error_message,
)
from compras_divididas.domain.money import quantize_money

logger = logging.getLogger(__name__)


class SessionProtocol(Protocol):
    """Subset of SQLAlchemy session APIs used by this service."""

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def refresh(self, instance: object) -> None: ...


class MovementRepositoryProtocol(Protocol):
    """Movement repository contract consumed by service."""

    def has_duplicate_external_id(
        self,
        *,
        competence_month: date,
        payer_participant_id: str,
        external_id: str,
    ) -> bool: ...

    def get_purchase_for_update(
        self, purchase_id: UUID
    ) -> FinancialMovement | None: ...

    def get_purchase_by_external_id_for_update(
        self,
        *,
        competence_month: date,
        payer_participant_id: str,
        external_id: str,
    ) -> FinancialMovement | None: ...

    def get_total_refunded_amount(self, original_purchase_id: UUID) -> Decimal: ...

    def add(self, movement: FinancialMovement) -> FinancialMovement: ...


class ParticipantRepositoryProtocol(Protocol):
    """Participant repository contract consumed by service."""

    def list_active_exactly_two(self) -> list[Participant]: ...


@dataclass(slots=True, frozen=True)
class CreateMovementInput:
    """Input model for append-only movement creation."""

    movement_type: MovementType
    amount: Decimal
    description: str
    requested_by_participant_id: str
    occurred_at: datetime | None = None
    payer_participant_id: str | None = None
    external_id: str | None = None
    original_purchase_id: UUID | None = None
    original_purchase_external_id: str | None = None


class MovementService:
    """Handles purchase and refund registration rules."""

    def __init__(
        self,
        *,
        movement_repository: MovementRepositoryProtocol,
        participant_repository: ParticipantRepositoryProtocol,
        session: SessionProtocol,
    ) -> None:
        self._movement_repository = movement_repository
        self._participant_repository = participant_repository
        self._session = session

    def create_movement(self, payload: CreateMovementInput) -> FinancialMovement:
        participants = self._participant_repository.list_active_exactly_two()
        participant_ids = {str(participant.id) for participant in participants}
        requested_by_participant_id = payload.requested_by_participant_id.strip()
        if requested_by_participant_id not in participant_ids:
            raise InvalidRequestError(
                message=compose_error_message(
                    cause=(
                        "requested_by_participant_id does not belong "
                        "to an active participant."
                    ),
                    action="Use one of the two active participant IDs and retry.",
                )
            )

        payer_participant_id = (
            payload.payer_participant_id or requested_by_participant_id
        )
        payer_participant_id = payer_participant_id.strip()
        if payer_participant_id not in participant_ids:
            raise InvalidRequestError(
                message=compose_error_message(
                    cause=(
                        "payer_participant_id does not belong to an active participant."
                    ),
                    action=(
                        "Use one of the two active participant IDs "
                        "or omit payer_participant_id."
                    ),
                )
            )

        occurred_at = resolve_occurred_at(payload.occurred_at)
        month = competence_month(occurred_at)
        amount = quantize_money(payload.amount)

        if amount <= Decimal("0"):
            raise InvalidRequestError(
                message=compose_error_message(
                    cause="Amount must be greater than zero.",
                    action="Provide a positive decimal amount with two digits.",
                )
            )

        external_id = payload.external_id.strip() if payload.external_id else None
        if external_id and self._movement_repository.has_duplicate_external_id(
            competence_month=month,
            payer_participant_id=payer_participant_id,
            external_id=external_id,
        ):
            raise DuplicateExternalIDError(
                message=compose_error_message(
                    cause=(
                        "external_id is already used for this participant "
                        "in this competence month."
                    ),
                    action="Send a unique external_id or omit this field.",
                )
            )

        try:
            original_purchase = self._resolve_original_purchase(
                payload=payload,
                competence_month_value=month,
                payer_participant_id=payer_participant_id,
            )

            movement = FinancialMovement(
                movement_type=payload.movement_type,
                amount=amount,
                description=payload.description.strip(),
                occurred_at=occurred_at,
                competence_month=month,
                payer_participant_id=payer_participant_id,
                requested_by_participant_id=requested_by_participant_id,
                external_id=external_id,
                original_purchase_id=original_purchase.id
                if original_purchase
                else None,
            )

            created_movement = self._movement_repository.add(movement)
            self._session.commit()
            self._session.refresh(created_movement)
            logger.info(
                "movement_created",
                extra={
                    "movement_id": str(created_movement.id),
                    "participant_id": requested_by_participant_id,
                    "competence_month": month.isoformat(),
                    "type": payload.movement_type.value,
                },
            )
            return created_movement
        except Exception:
            self._session.rollback()
            raise

    def _resolve_original_purchase(
        self,
        *,
        payload: CreateMovementInput,
        competence_month_value: date,
        payer_participant_id: str,
    ) -> FinancialMovement | None:
        if payload.movement_type == MovementType.PURCHASE:
            return None

        if payload.original_purchase_id:
            original_purchase = self._movement_repository.get_purchase_for_update(
                payload.original_purchase_id
            )
        elif payload.original_purchase_external_id:
            original_purchase = (
                self._movement_repository.get_purchase_by_external_id_for_update(
                    competence_month=competence_month_value,
                    payer_participant_id=payer_participant_id,
                    external_id=payload.original_purchase_external_id.strip(),
                )
            )
        else:
            raise InvalidRequestError(
                message=compose_error_message(
                    cause="Refund is missing original purchase reference.",
                    action=(
                        "Provide original_purchase_id or original_purchase_external_id."
                    ),
                )
            )

        if original_purchase is None:
            raise PurchaseNotFoundError(
                message=compose_error_message(
                    cause="Original purchase was not found for the provided reference.",
                    action=(
                        "Check purchase identifiers and competence context, then retry."
                    ),
                )
            )

        refunded_total = self._movement_repository.get_total_refunded_amount(
            original_purchase.id
        )
        candidate_total = refunded_total + quantize_money(payload.amount)
        if candidate_total > original_purchase.amount:
            logger.warning(
                "refund_rejected",
                extra={
                    "purchase_id": str(original_purchase.id),
                    "requested_refund_amount": str(payload.amount),
                    "already_refunded": str(refunded_total),
                },
            )
            raise RefundLimitExceededError(
                message=compose_error_message(
                    cause=(
                        "Refund exceeds the remaining refundable amount "
                        "of the purchase."
                    ),
                    action=(
                        "Use a lower refund value or reference the correct purchase."
                    ),
                )
            )
        return original_purchase
