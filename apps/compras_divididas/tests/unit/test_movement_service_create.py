from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from compras_divididas.db.models.financial_movement import (
    FinancialMovement,
    MovementType,
)
from compras_divididas.db.models.participant import Participant
from compras_divididas.domain.errors import DuplicateExternalIDError
from compras_divididas.services.movement_service import (
    CreateMovementInput,
    MovementService,
)


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def refresh(self, instance: object) -> None:
        _ = instance


class FakeParticipantRepository:
    def __init__(self, participant_ids: tuple[str, str]) -> None:
        self._participant_ids = participant_ids

    def list_active_exactly_two(self) -> list[Participant]:
        participant_a = Participant(
            id="ana",
            display_name="Ana",
            is_active=True,
        )
        participant_b = Participant(
            id="bia",
            display_name="Bia",
            is_active=True,
        )
        return [participant_a, participant_b]


@dataclass
class FakeMovementRepository:
    duplicate_external_ids: set[tuple[date, str, str]]
    movements: list[FinancialMovement] = field(default_factory=list)

    def has_duplicate_external_id(
        self,
        *,
        competence_month: date,
        payer_participant_id: str,
        external_id: str,
    ) -> bool:
        return (
            competence_month,
            payer_participant_id,
            external_id,
        ) in self.duplicate_external_ids

    def get_purchase_for_update(self, purchase_id: UUID) -> FinancialMovement | None:
        for movement in self.movements:
            if (
                movement.id == purchase_id
                and movement.movement_type == MovementType.PURCHASE
            ):
                return movement
        return None

    def get_purchase_by_external_id_for_update(
        self,
        *,
        competence_month: date,
        payer_participant_id: str,
        external_id: str,
    ) -> FinancialMovement | None:
        for movement in self.movements:
            if (
                movement.competence_month == competence_month
                and movement.payer_participant_id == payer_participant_id
                and movement.external_id == external_id
                and movement.movement_type == MovementType.PURCHASE
            ):
                return movement
        return None

    def get_total_refunded_amount(self, original_purchase_id: UUID) -> Decimal:
        refunded_total = Decimal("0.00")
        for movement in self.movements:
            if (
                movement.movement_type == MovementType.REFUND
                and movement.original_purchase_id == original_purchase_id
            ):
                refunded_total += movement.amount
        return refunded_total

    def add(self, movement: FinancialMovement) -> FinancialMovement:
        self.movements.append(movement)
        return movement


def test_create_movement_rounds_amount_with_half_up() -> None:
    participant_ids = ("ana", "bia")
    repository = FakeMovementRepository(duplicate_external_ids=set())
    session = FakeSession()
    service = MovementService(
        movement_repository=repository,
        participant_repository=FakeParticipantRepository(participant_ids),
        session=session,
    )

    movement = service.create_movement(
        CreateMovementInput(
            movement_type=MovementType.PURCHASE,
            amount=Decimal("10.005"),
            description="Compra",
            requested_by_participant_id=participant_ids[0],
        )
    )

    assert movement.amount == Decimal("10.01")
    assert session.committed is True


def test_create_movement_applies_default_payer_and_occurred_at() -> None:
    participant_ids = ("ana", "bia")
    repository = FakeMovementRepository(duplicate_external_ids=set())
    service = MovementService(
        movement_repository=repository,
        participant_repository=FakeParticipantRepository(participant_ids),
        session=FakeSession(),
    )

    movement = service.create_movement(
        CreateMovementInput(
            movement_type=MovementType.PURCHASE,
            amount=Decimal("25.00"),
            description="Compra",
            requested_by_participant_id=participant_ids[0],
            payer_participant_id=None,
            occurred_at=None,
        )
    )

    assert movement.payer_participant_id == participant_ids[0]
    assert movement.occurred_at.tzinfo is not None


def test_create_movement_rejects_duplicate_external_id() -> None:
    participant_ids = ("ana", "bia")
    repository = FakeMovementRepository(duplicate_external_ids=set())
    service = MovementService(
        movement_repository=repository,
        participant_repository=FakeParticipantRepository(participant_ids),
        session=FakeSession(),
    )

    expected_month = date(2026, 2, 1)
    repository.duplicate_external_ids.add((expected_month, participant_ids[0], "dup-1"))

    with pytest.raises(DuplicateExternalIDError):
        service.create_movement(
            CreateMovementInput(
                movement_type=MovementType.PURCHASE,
                amount=Decimal("10.00"),
                description="Compra",
                requested_by_participant_id=participant_ids[0],
                external_id="dup-1",
                occurred_at=datetime(2026, 2, 2, 10, 0, tzinfo=ZoneInfo("UTC")),
            )
        )
