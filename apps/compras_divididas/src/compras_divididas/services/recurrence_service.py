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
from compras_divididas.domain.errors import (
    DomainInvariantError,
    InvalidRecurrenceStateTransitionError,
    InvalidRequestError,
    RecurrenceNotFoundError,
    StartCompetenceLockedError,
)
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

    def get_rule_for_update(self, recurrence_id: UUID) -> RecurrenceRule | None: ...

    def update_rule(
        self,
        *,
        rule: RecurrenceRule,
        description: str | None,
        amount: Decimal | None,
        payer_participant_id: str | None,
        requested_by_participant_id: str,
        split_config: dict[str, object] | None,
        reference_day: int | None,
        start_competence_month: date | None,
        end_competence_month: date | None,
        clear_end_competence_month: bool,
    ) -> RecurrenceRule: ...

    def pause_rule(
        self,
        *,
        rule: RecurrenceRule,
    ) -> RecurrenceRule: ...

    def reactivate_rule(
        self,
        *,
        rule: RecurrenceRule,
    ) -> RecurrenceRule: ...

    def end_rule(
        self,
        *,
        rule: RecurrenceRule,
        end_competence_month: date | None,
    ) -> RecurrenceRule: ...


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


@dataclass(slots=True, frozen=True)
class UpdateRecurrenceInput:
    """Input model for recurrence update operation."""

    recurrence_id: UUID
    requested_by_participant_id: str
    description: str | None = None
    amount: str | None = None
    payer_participant_id: str | None = None
    split_config: dict[str, object] | None = None
    reference_day: int | None = None
    start_competence_month: date | None = None
    end_competence_month: date | None = None
    clear_end_competence_month: bool = False


@dataclass(slots=True, frozen=True)
class PauseRecurrenceInput:
    """Input model for pausing one recurrence."""

    recurrence_id: UUID
    requested_by_participant_id: str
    reason: str | None = None


@dataclass(slots=True, frozen=True)
class ReactivateRecurrenceInput:
    """Input model for reactivating one recurrence."""

    recurrence_id: UUID
    requested_by_participant_id: str


@dataclass(slots=True, frozen=True)
class EndRecurrenceInput:
    """Input model for ending one recurrence."""

    recurrence_id: UUID
    requested_by_participant_id: str
    end_competence_month: date | None = None


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

    def update_recurrence(self, payload: UpdateRecurrenceInput) -> RecurrenceRule:
        """Update mutable recurrence fields following last-write-wins."""

        participant_ids = self._active_participant_ids()
        self._ensure_requested_by_is_active(
            requested_by_participant_id=payload.requested_by_participant_id,
            participant_ids=participant_ids,
        )

        if (
            payload.payer_participant_id is not None
            and payload.payer_participant_id not in participant_ids
        ):
            raise InvalidRequestError(
                message=(
                    "Cause: payer_participant_id is not an active participant. "
                    "Action: Use one of the active participant IDs and retry."
                )
            )

        if payload.split_config is not None and (
            str(payload.split_config.get("mode", "")).strip() != "equal"
        ):
            raise DomainInvariantError(
                message=(
                    "Cause: split_config.mode is not supported for recurrences. "
                    "Action: Use split_config.mode equal for this version."
                )
            )

        amount = parse_money(payload.amount) if payload.amount is not None else None
        start_month = (
            normalize_competence_month(payload.start_competence_month)
            if payload.start_competence_month is not None
            else None
        )
        if payload.start_competence_month is not None and not is_first_day_of_month(
            payload.start_competence_month
        ):
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

        rule = self._require_rule_for_update(payload.recurrence_id)
        if (
            start_month is not None
            and rule.first_generated_competence_month is not None
            and start_month != rule.start_competence_month
        ):
            raise StartCompetenceLockedError(
                message=(
                    "Cause: start_competence_month cannot change after first "
                    "generation. Action: keep current start_competence_month and "
                    "edit other fields."
                ),
                details={"recurrence_id": str(rule.id)},
            )

        effective_start = start_month or rule.start_competence_month
        if payload.clear_end_competence_month:
            effective_end: date | None = None
        elif end_month is not None:
            effective_end = end_month
        else:
            effective_end = rule.end_competence_month

        if effective_end is not None and effective_end < effective_start:
            raise DomainInvariantError(
                message=(
                    "Cause: end_competence_month is earlier than "
                    "start_competence_month. Action: Use an equal or later "
                    "end_competence_month."
                )
            )

        try:
            updated_rule = self._recurrence_repository.update_rule(
                rule=rule,
                description=payload.description,
                amount=amount,
                payer_participant_id=payload.payer_participant_id,
                requested_by_participant_id=payload.requested_by_participant_id,
                split_config=payload.split_config,
                reference_day=payload.reference_day,
                start_competence_month=start_month,
                end_competence_month=end_month,
                clear_end_competence_month=payload.clear_end_competence_month,
            )
            self._recurrence_repository.add_event(
                recurrence_rule_id=updated_rule.id,
                event_type=RecurrenceEventType.RECURRENCE_UPDATED,
                actor_participant_id=payload.requested_by_participant_id,
                payload={
                    "status": updated_rule.status.value,
                    "next_competence_month": (
                        updated_rule.next_competence_month.isoformat()
                    ),
                },
            )
            self._session.commit()
            self._session.refresh(updated_rule)
            return updated_rule
        except Exception:
            self._session.rollback()
            raise

    def pause_recurrence(self, payload: PauseRecurrenceInput) -> RecurrenceRule:
        """Pause one active recurrence."""

        self._ensure_requested_by_is_active(
            requested_by_participant_id=payload.requested_by_participant_id,
            participant_ids=self._active_participant_ids(),
        )
        rule = self._require_rule_for_update(payload.recurrence_id)
        if rule.status != RecurrenceStatus.ACTIVE:
            raise InvalidRecurrenceStateTransitionError(
                details={
                    "from_status": rule.status.value,
                    "to_status": RecurrenceStatus.PAUSED.value,
                    "recurrence_id": str(rule.id),
                }
            )

        try:
            paused_rule = self._recurrence_repository.pause_rule(rule=rule)
            event_payload: dict[str, object] = {"status": paused_rule.status.value}
            if payload.reason is not None:
                event_payload["reason"] = payload.reason
            self._recurrence_repository.add_event(
                recurrence_rule_id=paused_rule.id,
                event_type=RecurrenceEventType.RECURRENCE_PAUSED,
                actor_participant_id=payload.requested_by_participant_id,
                payload=event_payload,
            )
            self._session.commit()
            self._session.refresh(paused_rule)
            return paused_rule
        except Exception:
            self._session.rollback()
            raise

    def reactivate_recurrence(
        self,
        payload: ReactivateRecurrenceInput,
    ) -> RecurrenceRule:
        """Reactivate one paused recurrence."""

        self._ensure_requested_by_is_active(
            requested_by_participant_id=payload.requested_by_participant_id,
            participant_ids=self._active_participant_ids(),
        )
        rule = self._require_rule_for_update(payload.recurrence_id)
        if rule.status != RecurrenceStatus.PAUSED:
            raise InvalidRecurrenceStateTransitionError(
                details={
                    "from_status": rule.status.value,
                    "to_status": RecurrenceStatus.ACTIVE.value,
                    "recurrence_id": str(rule.id),
                }
            )

        try:
            active_rule = self._recurrence_repository.reactivate_rule(rule=rule)
            self._recurrence_repository.add_event(
                recurrence_rule_id=active_rule.id,
                event_type=RecurrenceEventType.RECURRENCE_REACTIVATED,
                actor_participant_id=payload.requested_by_participant_id,
                payload={"status": active_rule.status.value},
            )
            self._session.commit()
            self._session.refresh(active_rule)
            return active_rule
        except Exception:
            self._session.rollback()
            raise

    def end_recurrence(self, payload: EndRecurrenceInput) -> RecurrenceRule:
        """End one active or paused recurrence."""

        self._ensure_requested_by_is_active(
            requested_by_participant_id=payload.requested_by_participant_id,
            participant_ids=self._active_participant_ids(),
        )
        rule = self._require_rule_for_update(payload.recurrence_id)
        if rule.status == RecurrenceStatus.ENDED:
            raise InvalidRecurrenceStateTransitionError(
                details={
                    "from_status": rule.status.value,
                    "to_status": RecurrenceStatus.ENDED.value,
                    "recurrence_id": str(rule.id),
                }
            )

        end_month = (
            normalize_competence_month(payload.end_competence_month)
            if payload.end_competence_month is not None
            else None
        )
        if end_month is not None and end_month < rule.start_competence_month:
            raise DomainInvariantError(
                message=(
                    "Cause: end_competence_month is earlier than "
                    "start_competence_month. Action: Use an equal or later "
                    "end_competence_month."
                )
            )

        try:
            ended_rule = self._recurrence_repository.end_rule(
                rule=rule,
                end_competence_month=end_month,
            )
            payload_data: dict[str, object] = {"status": ended_rule.status.value}
            if ended_rule.end_competence_month is not None:
                payload_data["end_competence_month"] = (
                    ended_rule.end_competence_month.isoformat()
                )
            self._recurrence_repository.add_event(
                recurrence_rule_id=ended_rule.id,
                event_type=RecurrenceEventType.RECURRENCE_ENDED,
                actor_participant_id=payload.requested_by_participant_id,
                payload=payload_data,
            )
            self._session.commit()
            self._session.refresh(ended_rule)
            return ended_rule
        except Exception:
            self._session.rollback()
            raise

    def _active_participant_ids(self) -> set[str]:
        participants = self._participant_repository.list_active_exactly_two()
        return {str(participant.id) for participant in participants}

    @staticmethod
    def _ensure_requested_by_is_active(
        *,
        requested_by_participant_id: str,
        participant_ids: set[str],
    ) -> None:
        if requested_by_participant_id not in participant_ids:
            raise InvalidRequestError(
                message=(
                    "Cause: requested_by_participant_id is not an active participant. "
                    "Action: Use one of the active participant IDs and retry."
                )
            )

    def _require_rule_for_update(self, recurrence_id: UUID) -> RecurrenceRule:
        rule = self._recurrence_repository.get_rule_for_update(recurrence_id)
        if rule is None:
            raise RecurrenceNotFoundError(details={"recurrence_id": str(recurrence_id)})
        return rule
