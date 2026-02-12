"""Recurrence routes."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from compras_divididas.api.dependencies import get_recurrence_service
from compras_divididas.api.schemas.recurrences import (
    CreateRecurrenceRequest,
    RecurrenceListResponse,
    RecurrenceResponse,
    parse_competence_month,
)
from compras_divididas.db.models.recurrence_rule import RecurrenceStatus
from compras_divididas.domain.errors import InvalidRequestError
from compras_divididas.services.recurrence_service import (
    CreateRecurrenceInput,
    ListRecurrenceInput,
    RecurrenceService,
)

router = APIRouter(prefix="/recurrences", tags=["Recurrences"])


@router.post(
    "",
    response_model=RecurrenceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid payload"},
        422: {"description": "Business rule violation"},
    },
)
def create_recurrence(
    payload: CreateRecurrenceRequest,
    service: Annotated[RecurrenceService, Depends(get_recurrence_service)],
) -> RecurrenceResponse:
    """Create one recurrence with active status."""

    recurrence = service.create_recurrence(
        CreateRecurrenceInput(
            description=payload.description,
            amount=payload.amount,
            payer_participant_id=payload.payer_participant_id,
            requested_by_participant_id=payload.requested_by_participant_id,
            split_config=payload.split_config,
            reference_day=payload.reference_day,
            start_competence_month=parse_competence_month(
                payload.start_competence_month
            ),
            end_competence_month=parse_competence_month(payload.end_competence_month)
            if payload.end_competence_month
            else None,
        )
    )
    return RecurrenceResponse.from_model(recurrence)


@router.get(
    "",
    response_model=RecurrenceListResponse,
    responses={
        400: {"description": "Invalid query filters"},
    },
)
def list_recurrences(
    service: Annotated[RecurrenceService, Depends(get_recurrence_service)],
    status: Annotated[Literal["active", "paused", "ended"] | None, Query()] = None,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RecurrenceListResponse:
    """List recurrences with optional status and competence filters."""

    competence_month: date | None = None
    if (year is None) != (month is None):
        raise InvalidRequestError(
            message=(
                "Cause: year and month filters must be provided together. "
                "Action: Send both year and month or omit both filters."
            )
        )
    if year is not None and month is not None:
        competence_month = date(year=year, month=month, day=1)

    status_filter = RecurrenceStatus(status) if status is not None else None
    items, total = service.list_recurrences(
        ListRecurrenceInput(
            status=status_filter,
            competence_month=competence_month,
            limit=limit,
            offset=offset,
        )
    )
    return RecurrenceListResponse.from_models(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
