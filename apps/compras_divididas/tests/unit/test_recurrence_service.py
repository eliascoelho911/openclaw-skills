"""Unit tests for recurrence service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from compras_divididas.db.models.participant import Participant
from compras_divididas.db.models.recurrence_event import RecurrenceEventType
from compras_divididas.db.models.recurrence_rule import (
    RecurrencePeriodicity,
    RecurrenceRule,
    RecurrenceStatus,
)
from compras_divididas.domain.errors import DomainInvariantError
from compras_divididas.services.recurrence_service import (
    CreateRecurrenceInput,
    RecurrenceService,
)
from compras_divididas.repositories.recurrence_repository import RecurrenceListFilters


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
        _ = event_type
        _ = payload
        _ = actor_participant_id
        _ = recurrence_occurrence_id
        return object()

    def list_rules(
        self,
        filters: RecurrenceListFilters,
    ) -> tuple[list[RecurrenceRule], int]:
        _ = filters
        return [], 0


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
