from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from compras_divididas.db.models.financial_movement import (
    FinancialMovement,
    MovementType,
)
from compras_divididas.db.models.participant import Participant
from compras_divididas.domain.errors import RefundLimitExceededError
from compras_divididas.repositories.movement_repository import MovementRepository
from compras_divididas.repositories.participant_repository import ParticipantRepository
from compras_divididas.services.movement_service import (
    CreateMovementInput,
    MovementService,
)


def seed_two_participants(session: Session) -> tuple[UUID, UUID]:
    participant_a = Participant(code="ana", display_name="Ana", is_active=True)
    participant_b = Participant(code="bia", display_name="Bia", is_active=True)
    session.add_all([participant_a, participant_b])
    session.commit()
    return participant_a.id, participant_b.id


def test_create_purchase_then_refund_and_enforce_refund_limit(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        participant_a_id, _ = seed_two_participants(session)

        service = MovementService(
            movement_repository=MovementRepository(session),
            participant_repository=ParticipantRepository(session),
            session=session,
        )

        purchase = service.create_movement(
            CreateMovementInput(
                movement_type=MovementType.PURCHASE,
                amount=Decimal("100.00"),
                description="Supermercado",
                requested_by_participant_id=participant_a_id,
                external_id="wpp-purchase-001",
            )
        )

        refund = service.create_movement(
            CreateMovementInput(
                movement_type=MovementType.REFUND,
                amount=Decimal("30.00"),
                description="Produto devolvido",
                requested_by_participant_id=participant_a_id,
                original_purchase_external_id="wpp-purchase-001",
            )
        )

        movements = list(
            session.scalars(
                select(FinancialMovement).order_by(FinancialMovement.created_at.asc())
            ).all()
        )
        assert len(movements) == 2
        assert refund.original_purchase_id == purchase.id
        net_total = movements[0].amount - movements[1].amount
        assert net_total == Decimal("70.00")

        with pytest.raises(RefundLimitExceededError):
            service.create_movement(
                CreateMovementInput(
                    movement_type=MovementType.REFUND,
                    amount=Decimal("80.00"),
                    description="Estorno excedente",
                    requested_by_participant_id=participant_a_id,
                    original_purchase_id=purchase.id,
                )
            )
