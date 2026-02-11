"""Movements routes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from compras_divididas.api.dependencies import (
    get_movement_query_repository,
    get_movement_service,
)
from compras_divididas.api.schemas.movement_list import MovementListResponse
from compras_divididas.api.schemas.movements import (
    CreateMovementRequest,
    MovementResponse,
)
from compras_divididas.db.models.financial_movement import MovementType
from compras_divididas.repositories.movement_query_repository import (
    MovementQueryFilters,
    MovementQueryRepository,
)
from compras_divididas.services.movement_service import (
    CreateMovementInput,
    MovementService,
)

router = APIRouter(prefix="/movements", tags=["Movements"])


@router.get(
    "",
    response_model=MovementListResponse,
    responses={
        400: {"description": "Filtros invalidos"},
    },
)
def list_movements(
    year: Annotated[int, Query(ge=2000, le=2100)],
    month: Annotated[int, Query(ge=1, le=12)],
    query_repository: Annotated[
        MovementQueryRepository,
        Depends(get_movement_query_repository),
    ],
    type: Annotated[Literal["purchase", "refund"] | None, Query()] = None,
    description: Annotated[str | None, Query(min_length=1, max_length=280)] = None,
    amount: Annotated[str | None, Query(pattern=r"^[0-9]+\.[0-9]{2}$")] = None,
    participant_id: UUID | None = None,
    external_id: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MovementListResponse:
    """List monthly movements with optional filters and pagination."""

    filters = MovementQueryFilters(
        competence_month=date(year=year, month=month, day=1),
        movement_type=MovementType(type) if type else None,
        description=description.strip() if description else None,
        amount=Decimal(amount) if amount else None,
        participant_id=participant_id,
        external_id=external_id.strip() if external_id else None,
        limit=limit,
        offset=offset,
    )
    items, total = query_repository.list_movements(filters)
    return MovementListResponse.from_models(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


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
