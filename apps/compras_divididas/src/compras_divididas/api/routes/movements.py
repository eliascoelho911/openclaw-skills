"""Movements routes."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status

from compras_divididas.api.dependencies import get_movement_service
from compras_divididas.api.schemas.movements import (
    CreateMovementRequest,
    MovementResponse,
)
from compras_divididas.db.models.financial_movement import MovementType
from compras_divididas.services.movement_service import (
    CreateMovementInput,
    MovementService,
)

router = APIRouter(prefix="/movements", tags=["Movements"])


@router.post(
    "",
    response_model=MovementResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Payload invalido"},
        404: {"description": "Compra original nao encontrada"},
        409: {"description": "Duplicidade por external_id"},
        422: {"description": "Regra de negocio violada"},
    },
)
def create_movement(
    payload: CreateMovementRequest,
    service: Annotated[MovementService, Depends(get_movement_service)],
) -> MovementResponse:
    """Register a purchase or refund movement in append-only mode."""

    movement = service.create_movement(
        CreateMovementInput(
            movement_type=MovementType(payload.type),
            amount=Decimal(payload.amount),
            description=payload.description,
            occurred_at=payload.occurred_at,
            payer_participant_id=payload.payer_participant_id,
            requested_by_participant_id=payload.requested_by_participant_id,
            external_id=payload.external_id,
            original_purchase_id=payload.original_purchase_id,
            original_purchase_external_id=payload.original_purchase_external_id,
        )
    )
    return MovementResponse.from_model(movement)
