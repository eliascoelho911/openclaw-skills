"""Recurrence routes."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, status

from compras_divididas.api.dependencies import (
    get_recurrence_generation_service,
    get_recurrence_service,
)
from compras_divididas.api.schemas.recurrences import (
    CreateRecurrenceRequest,
    EndRecurrenceRequest,
    GenerateRecurrencesRequest,
    GenerateRecurrencesResponse,
    PauseRecurrenceRequest,
    ReactivateRecurrenceRequest,
    RecurrenceListResponse,
    RecurrenceResponse,
    UpdateRecurrenceRequest,
    parse_competence_month,
)
from compras_divididas.db.models.recurrence_rule import RecurrenceStatus
from compras_divididas.domain.errors import InvalidRequestError
from compras_divididas.services.recurrence_generation_service import (
    RecurrenceGenerationService,
)
from compras_divididas.services.recurrence_service import (
    CreateRecurrenceInput,
    EndRecurrenceInput,
    ListRecurrenceInput,
    PauseRecurrenceInput,
    ReactivateRecurrenceInput,
    RecurrenceService,
    UpdateRecurrenceInput,
)

router = APIRouter(prefix="/recurrences", tags=["Recurrences"])
monthly_generation_router = APIRouter(
    prefix="/months",
    tags=["Monthly Recurrence Generation"],
)


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


@router.patch(
    "/{recurrence_id}",
    response_model=RecurrenceResponse,
    responses={
        400: {"description": "Invalid payload"},
        404: {"description": "Recurrence not found"},
        422: {"description": "Business rule violation"},
    },
)
def update_recurrence(
    recurrence_id: UUID,
    payload: UpdateRecurrenceRequest,
    service: Annotated[RecurrenceService, Depends(get_recurrence_service)],
) -> RecurrenceResponse:
    """Update one recurrence using last-write-wins semantics."""

    recurrence = service.update_recurrence(
        UpdateRecurrenceInput(
            recurrence_id=recurrence_id,
            requested_by_participant_id=payload.requested_by_participant_id,
            description=payload.description,
            amount=payload.amount,
            payer_participant_id=payload.payer_participant_id,
            split_config=payload.split_config,
            reference_day=payload.reference_day,
            start_competence_month=parse_competence_month(
                payload.start_competence_month
            )
            if payload.start_competence_month is not None
            else None,
            end_competence_month=parse_competence_month(payload.end_competence_month)
            if payload.end_competence_month is not None
            else None,
            clear_end_competence_month=(
                "end_competence_month" in payload.model_fields_set
                and payload.end_competence_month is None
            ),
        )
    )
    return RecurrenceResponse.from_model(recurrence)


@router.post(
    "/{recurrence_id}/pause",
    response_model=RecurrenceResponse,
    responses={
        404: {"description": "Recurrence not found"},
        422: {"description": "Invalid state transition"},
    },
)
def pause_recurrence(
    recurrence_id: UUID,
    payload: PauseRecurrenceRequest,
    service: Annotated[RecurrenceService, Depends(get_recurrence_service)],
) -> RecurrenceResponse:
    """Pause one active recurrence."""

    recurrence = service.pause_recurrence(
        PauseRecurrenceInput(
            recurrence_id=recurrence_id,
            requested_by_participant_id=payload.requested_by_participant_id,
            reason=payload.reason,
        )
    )
    return RecurrenceResponse.from_model(recurrence)


@router.post(
    "/{recurrence_id}/reactivate",
    response_model=RecurrenceResponse,
    responses={
        404: {"description": "Recurrence not found"},
        422: {"description": "Invalid state transition"},
    },
)
def reactivate_recurrence(
    recurrence_id: UUID,
    payload: ReactivateRecurrenceRequest,
    service: Annotated[RecurrenceService, Depends(get_recurrence_service)],
) -> RecurrenceResponse:
    """Reactivate one paused recurrence."""

    recurrence = service.reactivate_recurrence(
        ReactivateRecurrenceInput(
            recurrence_id=recurrence_id,
            requested_by_participant_id=payload.requested_by_participant_id,
        )
    )
    return RecurrenceResponse.from_model(recurrence)


@router.post(
    "/{recurrence_id}/end",
    response_model=RecurrenceResponse,
    responses={
        404: {"description": "Recurrence not found"},
        422: {"description": "Invalid state transition"},
    },
)
def end_recurrence(
    recurrence_id: UUID,
    payload: EndRecurrenceRequest,
    service: Annotated[RecurrenceService, Depends(get_recurrence_service)],
) -> RecurrenceResponse:
    """End one recurrence permanently."""

    recurrence = service.end_recurrence(
        EndRecurrenceInput(
            recurrence_id=recurrence_id,
            requested_by_participant_id=payload.requested_by_participant_id,
            end_competence_month=parse_competence_month(payload.end_competence_month)
            if payload.end_competence_month is not None
            else None,
        )
    )
    return RecurrenceResponse.from_model(recurrence)


@monthly_generation_router.post(
    "/{year}/{month}/recurrences/generate",
    response_model=GenerateRecurrencesResponse,
)
def generate_recurrences_for_month(
    year: Annotated[int, Path(ge=2000, le=2100)],
    month: Annotated[int, Path(ge=1, le=12)],
    service: Annotated[
        RecurrenceGenerationService,
        Depends(get_recurrence_generation_service),
    ],
    payload: Annotated[
        GenerateRecurrencesRequest,
        Body(default_factory=GenerateRecurrencesRequest),
    ],
) -> GenerateRecurrencesResponse:
    """Generate monthly recurrence movements idempotently."""

    competence_month = date(year=year, month=month, day=1)
    result = service.generate_for_month(
        competence_month=competence_month,
        requested_by_participant_id=payload.requested_by_participant_id,
        include_blocked_details=payload.include_blocked_details,
        dry_run=payload.dry_run,
    )
    return GenerateRecurrencesResponse.from_result(
        result,
        include_blocked_details=payload.include_blocked_details,
    )
