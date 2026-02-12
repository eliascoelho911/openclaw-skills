"""Recurrence rule service layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from compras_divididas.db.models.participant import Participant
from compras_divididas.db.models.recurrence_event import RecurrenceEventType
from compras_divididas.db.models.recurrence_rule import RecurrenceRule, RecurrenceStatus
from compras_divididas.domain.errors import DomainInvariantError, InvalidRequestError
from compras_divididas.domain.money import parse_money
from compras_divididas.domain.recurrence_schedule import (
    is_first_day_of_month,
    normalize_competence_month,
)
from compras_divididas.repositories.recurrence_repository import (
    RecurrenceListFilters,
)


class SessionProtocol(Protocol):
    """Subset of SQLAlchemy session APIs used by recurrence service."""

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def refresh(self, instance: object) -> None: ...


class ParticipantRepositoryProtocol(Protocol):
    """Participant repository contract consumed by recurrence service."""

    def list_active_exactly_two(self) -> list[Participant]: ...


class RecurrenceRepositoryProtocol(Protocol):
    """Recurrence repository contract consumed by service."""

    def add_rule(
        self,
        *,
        description: str,
        amount: Decimal,
        payer_participant_id: str,
        requested_by_participant_id: str,
        split_config: dict[str, object],
        reference_day: int,
        start_competence_month: date,
        end_competence_month: date | None,
        next_competence_month: date,
    ) -> RecurrenceRule: ...

    def add_event(
        self,
        *,
        recurrence_rule_id: UUID,
        event_type: RecurrenceEventType,
        payload: dict[str, object],
        actor_participant_id: str | None = None,
        recurrence_occurrence_id: UUID | None = None,
    ) -> object: ...

    def list_rules(
        self,
        filters: RecurrenceListFilters,
    ) -> tuple[list[RecurrenceRule], int]: ...


@dataclass(slots=True, frozen=True)
class CreateRecurrenceInput:
    """Input model for recurrence creation."""

    description: str
    amount: str
    payer_participant_id: str
    requested_by_participant_id: str
    split_config: dict[str, object]
    reference_day: int
    start_competence_month: date
    end_competence_month: date | None = None


@dataclass(slots=True, frozen=True)
class ListRecurrenceInput:
    """Input model for recurrence listing."""

    status: RecurrenceStatus | None = None
    competence_month: date | None = None
    limit: int = 50
    offset: int = 0


class RecurrenceService:
    """Coordinates recurrence rule use cases."""

    def __init__(
        self,
        *,
        recurrence_repository: RecurrenceRepositoryProtocol,
        participant_repository: ParticipantRepositoryProtocol,
        session: SessionProtocol,
    ) -> None:
        self._recurrence_repository = recurrence_repository
        self._participant_repository = participant_repository
        self._session = session

    def create_recurrence(self, payload: CreateRecurrenceInput) -> RecurrenceRule:
        """Create one active monthly recurrence after business validation."""

        participants = self._participant_repository.list_active_exactly_two()
        participant_ids = {str(participant.id) for participant in participants}

        if payload.requested_by_participant_id not in participant_ids:
            raise InvalidRequestError(
                message=(
                    "Cause: requested_by_participant_id is not an active "
                    "participant. Action: Use one of the active participant IDs "
                    "and retry."
                )
            )

        if payload.payer_participant_id not in participant_ids:
            raise InvalidRequestError(
                message=(
                    "Cause: payer_participant_id is not an active participant. "
                    "Action: Use one of the active participant IDs and retry."
                )
            )

        if payload.end_competence_month and (
            payload.end_competence_month < payload.start_competence_month
        ):
            raise DomainInvariantError(
                message=(
                    "Cause: end_competence_month is earlier than "
                    "start_competence_month. Action: Use an equal or later "
                    "end_competence_month."
                )
            )

        split_mode = str(payload.split_config.get("mode", "")).strip()
        if split_mode != "equal":
            raise DomainInvariantError(
                message=(
                    "Cause: split_config.mode is not supported for recurrences. "
                    "Action: Use split_config.mode equal for this version."
                )
            )

        start_month = normalize_competence_month(payload.start_competence_month)
        if not is_first_day_of_month(payload.start_competence_month):
            raise InvalidRequestError(
                message=(
                    "Cause: start_competence_month must be the first day of the "
                    "month. Action: Send start_competence_month in YYYY-MM format."
                )
            )

        end_month = (
            normalize_competence_month(payload.end_competence_month)
            if payload.end_competence_month is not None
            else None
        )

        amount = parse_money(payload.amount)

        try:
            next_competence_month = start_month.isoformat()
            recurrence = self._recurrence_repository.add_rule(
                description=payload.description.strip(),
                amount=amount,
                payer_participant_id=payload.payer_participant_id,
                requested_by_participant_id=payload.requested_by_participant_id,
                split_config=dict(payload.split_config),
                reference_day=payload.reference_day,
                start_competence_month=start_month,
                end_competence_month=end_month,
                next_competence_month=start_month,
            )
            self._recurrence_repository.add_event(
                recurrence_rule_id=recurrence.id,
                event_type=RecurrenceEventType.RECURRENCE_CREATED,
                actor_participant_id=payload.requested_by_participant_id,
                payload={
                    "status": recurrence.status.value,
                    "next_competence_month": next_competence_month,
                },
            )
            self._session.commit()
            self._session.refresh(recurrence)
            return recurrence
        except Exception:
            self._session.rollback()
            raise

    def list_recurrences(
        self,
        payload: ListRecurrenceInput,
    ) -> tuple[list[RecurrenceRule], int]:
        """List recurrences with status and competence filters."""

        return self._recurrence_repository.list_rules(
            RecurrenceListFilters(
                status=payload.status,
                competence_month=payload.competence_month,
                limit=payload.limit,
                offset=payload.offset,
            )
        )
