"""API dependency providers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from compras_divididas.db.session import get_db_session
from compras_divididas.repositories.movement_query_repository import (
    MovementQueryRepository,
)
from compras_divididas.repositories.movement_repository import MovementRepository
from compras_divididas.repositories.participant_repository import ParticipantRepository
from compras_divididas.services.monthly_summary_service import MonthlySummaryService
from compras_divididas.services.movement_service import MovementService


def get_movement_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> MovementService:
    """Build movement service with per-request session."""

    movement_repository = MovementRepository(session)
    participant_repository = ParticipantRepository(session)
    return MovementService(
        movement_repository=movement_repository,
        participant_repository=participant_repository,
        session=session,
    )


def get_movement_query_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> MovementQueryRepository:
    """Build movement query repository with per-request session."""

    return MovementQueryRepository(session)


def get_monthly_summary_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> MonthlySummaryService:
    """Build monthly summary service with query/participant repositories."""

    return MonthlySummaryService(
        participant_repository=ParticipantRepository(session),
        movement_query_repository=MovementQueryRepository(session),
    )
