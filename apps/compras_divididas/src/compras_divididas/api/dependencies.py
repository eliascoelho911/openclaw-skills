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
from compras_divididas.repositories.recurrence_repository import RecurrenceRepository
from compras_divididas.services.monthly_report_service import MonthlyReportService
from compras_divididas.services.monthly_summary_service import MonthlySummaryService
from compras_divididas.services.movement_service import MovementService
from compras_divididas.services.recurrence_generation_service import (
    RecurrenceGenerationService,
)
from compras_divididas.services.recurrence_service import RecurrenceService


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


def get_participant_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> ParticipantRepository:
    """Build participant repository with per-request session."""

    return ParticipantRepository(session)


def get_monthly_summary_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> MonthlySummaryService:
    """Build monthly summary service with query/participant repositories."""

    recurrence_generation_service = RecurrenceGenerationService(
        recurrence_repository=RecurrenceRepository(session),
        session=session,
    )
    return MonthlySummaryService(
        participant_repository=ParticipantRepository(session),
        movement_query_repository=MovementQueryRepository(session),
        recurrence_generation_service=recurrence_generation_service,
    )


def get_monthly_report_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> MonthlyReportService:
    """Build monthly report service reusing summary aggregation service."""

    recurrence_generation_service = RecurrenceGenerationService(
        recurrence_repository=RecurrenceRepository(session),
        session=session,
    )
    summary_service = MonthlySummaryService(
        participant_repository=ParticipantRepository(session),
        movement_query_repository=MovementQueryRepository(session),
        recurrence_generation_service=recurrence_generation_service,
    )
    return MonthlyReportService(monthly_summary_service=summary_service)


def get_recurrence_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> RecurrenceRepository:
    """Build recurrence repository with per-request session."""

    return RecurrenceRepository(session)


def get_recurrence_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> RecurrenceService:
    """Build recurrence service with per-request session."""

    return RecurrenceService(
        recurrence_repository=RecurrenceRepository(session),
        participant_repository=ParticipantRepository(session),
        session=session,
    )


def get_recurrence_generation_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> RecurrenceGenerationService:
    """Build recurrence generation service."""

    return RecurrenceGenerationService(
        recurrence_repository=RecurrenceRepository(session),
        session=session,
    )
