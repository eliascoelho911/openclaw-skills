"""Participants routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from compras_divididas.api.dependencies import get_participant_repository
from compras_divididas.api.schemas.participants import ParticipantsListResponse
from compras_divididas.repositories.participant_repository import ParticipantRepository

router = APIRouter(prefix="/participants", tags=["Participants"])


@router.get("", response_model=ParticipantsListResponse)
def list_participants(
    repository: Annotated[ParticipantRepository, Depends(get_participant_repository)],
) -> ParticipantsListResponse:
    """List active participants used by the reconciliation flow."""

    participants = repository.list_active_exactly_two()
    return ParticipantsListResponse.from_models(participants)
