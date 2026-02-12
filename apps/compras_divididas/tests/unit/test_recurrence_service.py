"""Unit tests for recurrence service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from compras_divididas.db.models.participant import Participant
from compras_divididas.db.models.recurrence_event import RecurrenceEventType
from compras_divididas.db.models.recurrence_rule import (
    RecurrencePeriodicity,
    RecurrenceRule,
    RecurrenceStatus,
)
from compras_divididas.domain.errors import (
    DomainInvariantError,
    InvalidRecurrenceStateTransitionError,
    StartCompetenceLockedError,
)
from compras_divididas.repositories.recurrence_repository import RecurrenceListFilters
from compras_divididas.services.recurrence_service import (
    CreateRecurrenceInput,
    EndRecurrenceInput,
    PauseRecurrenceInput,
    ReactivateRecurrenceInput,
    RecurrenceService,
    UpdateRecurrenceInput,
)


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def refresh(self, instance: object) -> None:
        _ = instance


class FakeParticipantRepository:
    def list_active_exactly_two(self) -> list[Participant]:
        return [
            Participant(id="ana", display_name="Ana", is_active=True),
            Participant(id="bia", display_name="Bia", is_active=True),
        ]


@dataclass
class FakeRecurrenceRepository:
    created_rule: RecurrenceRule | None = None
    event_types: list[RecurrenceEventType] | None = None

    def __post_init__(self) -> None:
        if self.event_types is None:
            self.event_types = []

    @staticmethod
    def _rule_fixture() -> RecurrenceRule:
        return RecurrenceRule(
            id=uuid4(),
            description="Internet",
            amount=Decimal("120.00"),
            payer_participant_id="ana",
            requested_by_participant_id="ana",
            split_config={"mode": "equal"},
            periodicity=RecurrencePeriodicity.MONTHLY,
            reference_day=31,
            start_competence_month=date(2026, 2, 1),
            end_competence_month=None,
            status=RecurrenceStatus.ACTIVE,
            first_generated_competence_month=None,
            last_generated_competence_month=None,
            next_competence_month=date(2026, 2, 1),
            version=1,
        )

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
    ) -> RecurrenceRule:
        rule = RecurrenceRule(
            description=description,
            amount=amount,
            payer_participant_id=payer_participant_id,
            requested_by_participant_id=requested_by_participant_id,
            split_config=split_config,
            periodicity=RecurrencePeriodicity.MONTHLY,
            reference_day=reference_day,
            start_competence_month=start_competence_month,
            end_competence_month=end_competence_month,
            status=RecurrenceStatus.ACTIVE,
            first_generated_competence_month=None,
            last_generated_competence_month=None,
            next_competence_month=next_competence_month,
            version=1,
        )
        self.created_rule = rule
        return rule

    def add_event(
        self,
        *,
        recurrence_rule_id: UUID,
        event_type: RecurrenceEventType,
        payload: dict[str, object],
        actor_participant_id: str | None = None,
        recurrence_occurrence_id: UUID | None = None,
    ) -> object:
        _ = recurrence_rule_id
        _ = payload
        _ = actor_participant_id
        _ = recurrence_occurrence_id
        assert self.event_types is not None
        self.event_types.append(event_type)
        return object()

    def list_rules(
        self,
        filters: RecurrenceListFilters,
    ) -> tuple[list[RecurrenceRule], int]:
        _ = filters
        return [], 0

    def get_rule_for_update(self, recurrence_id: UUID) -> RecurrenceRule | None:
        _ = recurrence_id
        if self.created_rule is None:
            self.created_rule = self._rule_fixture()
        return self.created_rule

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
    ) -> RecurrenceRule:
        if description is not None:
            rule.description = description
        if amount is not None:
            rule.amount = amount
        if payer_participant_id is not None:
            rule.payer_participant_id = payer_participant_id
        if split_config is not None:
            rule.split_config = split_config
        if reference_day is not None:
            rule.reference_day = reference_day
        if start_competence_month is not None:
            rule.start_competence_month = start_competence_month
        if clear_end_competence_month:
            rule.end_competence_month = None
        elif end_competence_month is not None:
            rule.end_competence_month = end_competence_month
        rule.requested_by_participant_id = requested_by_participant_id
        return rule

    def pause_rule(self, *, rule: RecurrenceRule) -> RecurrenceRule:
        rule.status = RecurrenceStatus.PAUSED
        return rule

    def reactivate_rule(self, *, rule: RecurrenceRule) -> RecurrenceRule:
        rule.status = RecurrenceStatus.ACTIVE
        return rule

    def end_rule(
        self,
        *,
        rule: RecurrenceRule,
        end_competence_month: date | None,
    ) -> RecurrenceRule:
        rule.status = RecurrenceStatus.ENDED
        if end_competence_month is not None:
            rule.end_competence_month = end_competence_month
        return rule


def test_create_recurrence_sets_next_competence_to_start_month() -> None:
    repository = FakeRecurrenceRepository()
    session = FakeSession()
    service = RecurrenceService(
        recurrence_repository=repository,
        participant_repository=FakeParticipantRepository(),
        session=session,
    )

    recurrence = service.create_recurrence(
        CreateRecurrenceInput(
            description="Internet",
            amount="120.00",
            payer_participant_id="ana",
            requested_by_participant_id="ana",
            split_config={"mode": "equal"},
            reference_day=31,
            start_competence_month=date(2026, 2, 1),
        )
    )

    assert recurrence.next_competence_month == date(2026, 2, 1)
    assert recurrence.amount == Decimal("120.00")
    assert session.committed is True


def test_create_recurrence_rejects_end_month_before_start_month() -> None:
    service = RecurrenceService(
        recurrence_repository=FakeRecurrenceRepository(),
        participant_repository=FakeParticipantRepository(),
        session=FakeSession(),
    )

    with pytest.raises(DomainInvariantError):
        service.create_recurrence(
            CreateRecurrenceInput(
                description="Internet",
                amount="120.00",
                payer_participant_id="ana",
                requested_by_participant_id="ana",
                split_config={"mode": "equal"},
                reference_day=31,
                start_competence_month=date(2026, 2, 1),
                end_competence_month=date(2026, 1, 1),
            )
        )


def test_create_recurrence_rejects_unsupported_split_mode() -> None:
    service = RecurrenceService(
        recurrence_repository=FakeRecurrenceRepository(),
        participant_repository=FakeParticipantRepository(),
        session=FakeSession(),
    )

    with pytest.raises(DomainInvariantError):
        service.create_recurrence(
            CreateRecurrenceInput(
                description="Internet",
                amount="120.00",
                payer_participant_id="ana",
                requested_by_participant_id="ana",
                split_config={"mode": "weighted"},
                reference_day=31,
                start_competence_month=date(2026, 2, 1),
            )
        )


def test_update_recurrence_applies_last_write_wins() -> None:
    repository = FakeRecurrenceRepository()
    service = RecurrenceService(
        recurrence_repository=repository,
        participant_repository=FakeParticipantRepository(),
        session=FakeSession(),
    )

    recurrence = repository.get_rule_for_update(uuid4())
    assert recurrence is not None

    first_update = service.update_recurrence(
        UpdateRecurrenceInput(
            recurrence_id=recurrence.id,
            requested_by_participant_id="ana",
            description="Internet fibra",
            amount="139.90",
        )
    )
    second_update = service.update_recurrence(
        UpdateRecurrenceInput(
            recurrence_id=recurrence.id,
            requested_by_participant_id="ana",
            description="Internet ultra",
            amount="149.90",
        )
    )

    assert first_update.description == "Internet ultra"
    assert second_update.description == "Internet ultra"
    assert second_update.amount == Decimal("149.90")


def test_update_recurrence_locks_start_month_after_first_generation() -> None:
    repository = FakeRecurrenceRepository()
    recurrence = repository.get_rule_for_update(uuid4())
    assert recurrence is not None
    recurrence.first_generated_competence_month = date(2026, 2, 1)

    service = RecurrenceService(
        recurrence_repository=repository,
        participant_repository=FakeParticipantRepository(),
        session=FakeSession(),
    )

    with pytest.raises(StartCompetenceLockedError):
        service.update_recurrence(
            UpdateRecurrenceInput(
                recurrence_id=recurrence.id,
                requested_by_participant_id="ana",
                start_competence_month=date(2026, 1, 1),
            )
        )


def test_pause_and_reactivate_follow_state_transitions() -> None:
    repository = FakeRecurrenceRepository()
    recurrence = repository.get_rule_for_update(uuid4())
    assert recurrence is not None

    service = RecurrenceService(
        recurrence_repository=repository,
        participant_repository=FakeParticipantRepository(),
        session=FakeSession(),
    )

    paused = service.pause_recurrence(
        PauseRecurrenceInput(
            recurrence_id=recurrence.id,
            requested_by_participant_id="ana",
            reason="Temporary stop",
        )
    )
    assert paused.status == RecurrenceStatus.PAUSED

    reactivated = service.reactivate_recurrence(
        ReactivateRecurrenceInput(
            recurrence_id=recurrence.id,
            requested_by_participant_id="ana",
        )
    )
    assert reactivated.status == RecurrenceStatus.ACTIVE


def test_end_recurrence_rejects_terminal_transition() -> None:
    repository = FakeRecurrenceRepository()
    recurrence = repository.get_rule_for_update(uuid4())
    assert recurrence is not None

    service = RecurrenceService(
        recurrence_repository=repository,
        participant_repository=FakeParticipantRepository(),
        session=FakeSession(),
    )

    ended = service.end_recurrence(
        EndRecurrenceInput(
            recurrence_id=recurrence.id,
            requested_by_participant_id="ana",
            end_competence_month=date(2026, 12, 1),
        )
    )
    assert ended.status == RecurrenceStatus.ENDED

    with pytest.raises(InvalidRecurrenceStateTransitionError):
        service.end_recurrence(
            EndRecurrenceInput(
                recurrence_id=recurrence.id,
                requested_by_participant_id="ana",
            )
        )
