"""Persistence operations for recurrence entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from compras_divididas.db.models.financial_movement import (
    FinancialMovement,
    MovementType,
)
from compras_divididas.db.models.recurrence_event import (
    RecurrenceEvent,
    RecurrenceEventType,
)
from compras_divididas.db.models.recurrence_occurrence import (
    RecurrenceOccurrence,
    RecurrenceOccurrenceStatus,
)
from compras_divididas.db.models.recurrence_rule import (
    RecurrencePeriodicity,
    RecurrenceRule,
    RecurrenceStatus,
)


@dataclass(slots=True, frozen=True)
class EligibleRecurrenceRuleFilters:
    """Filters for selecting rules eligible for generation."""

    competence_month: date
    limit: int = 100


@dataclass(slots=True, frozen=True)
class RecurrenceListFilters:
    """Filters for listing recurrences."""

    status: RecurrenceStatus | None = None
    competence_month: date | None = None
    limit: int = 50
    offset: int = 0


class RecurrenceRepository:
    """Repository for recurrence rules, occurrences and events."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_rule(self, recurrence_id: UUID) -> RecurrenceRule | None:
        """Fetch recurrence rule by id."""

        statement = select(RecurrenceRule).where(RecurrenceRule.id == recurrence_id)
        return self._session.scalar(statement)

    def get_rule_for_update(self, recurrence_id: UUID) -> RecurrenceRule | None:
        """Fetch and lock one recurrence rule by id."""

        statement = (
            select(RecurrenceRule)
            .where(RecurrenceRule.id == recurrence_id)
            .with_for_update()
        )
        return self._session.scalar(statement)

    def add_rule(
        self,
        *,
        description: str,
        amount: Decimal,
        payer_participant_id: str,
        requested_by_participant_id: str,
        split_config: dict[str, Any],
        reference_day: int,
        start_competence_month: date,
        end_competence_month: date | None,
        next_competence_month: date,
    ) -> RecurrenceRule:
        """Persist a newly created recurrence rule."""

        now = datetime.now(tz=UTC)
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
            created_at=now,
            updated_at=now,
        )
        self._session.add(rule)
        self._session.flush()
        return rule

    def list_rules(
        self,
        filters: RecurrenceListFilters,
    ) -> tuple[list[RecurrenceRule], int]:
        """List recurrence rules with optional status and month eligibility."""

        statement = self._apply_list_filters(select(RecurrenceRule), filters)
        total_statement = select(func.count()).select_from(statement.subquery())
        total = int(self._session.scalar(total_statement) or 0)

        page_statement = (
            statement.order_by(
                RecurrenceRule.created_at.desc(), RecurrenceRule.id.desc()
            )
            .limit(filters.limit)
            .offset(filters.offset)
        )
        items = list(self._session.scalars(page_statement).all())
        return items, total

    def list_eligible_rules_for_generation(
        self,
        filters: EligibleRecurrenceRuleFilters,
    ) -> list[RecurrenceRule]:
        """Fetch and lock eligible active rules for one competence month."""

        competence_month = filters.competence_month
        statement = (
            select(RecurrenceRule)
            .where(
                RecurrenceRule.status == RecurrenceStatus.ACTIVE,
                RecurrenceRule.start_competence_month <= competence_month,
                or_(
                    RecurrenceRule.end_competence_month.is_(None),
                    RecurrenceRule.end_competence_month >= competence_month,
                ),
                RecurrenceRule.next_competence_month <= competence_month,
            )
            .order_by(RecurrenceRule.next_competence_month, RecurrenceRule.id)
            .limit(filters.limit)
            .with_for_update(skip_locked=True)
        )
        return list(self._session.scalars(statement))

    def get_occurrence(
        self,
        *,
        recurrence_rule_id: UUID,
        competence_month: date,
    ) -> RecurrenceOccurrence | None:
        """Fetch one occurrence by recurrence rule and competence month."""

        statement = select(RecurrenceOccurrence).where(
            RecurrenceOccurrence.recurrence_rule_id == recurrence_rule_id,
            RecurrenceOccurrence.competence_month == competence_month,
        )
        return self._session.scalar(statement)

    def get_occurrence_for_update(
        self,
        *,
        recurrence_rule_id: UUID,
        competence_month: date,
    ) -> RecurrenceOccurrence | None:
        """Fetch and lock one occurrence by recurrence rule and month."""

        statement = (
            select(RecurrenceOccurrence)
            .where(
                RecurrenceOccurrence.recurrence_rule_id == recurrence_rule_id,
                RecurrenceOccurrence.competence_month == competence_month,
            )
            .with_for_update()
        )
        return self._session.scalar(statement)

    def create_pending_occurrence_if_missing(
        self,
        *,
        recurrence_rule_id: UUID,
        competence_month: date,
        scheduled_date: date,
    ) -> tuple[RecurrenceOccurrence, bool]:
        """Create pending occurrence idempotently for recurrence + month."""

        duplicate_error: IntegrityError | None = None
        with self._session.begin_nested():
            occurrence = RecurrenceOccurrence(
                recurrence_rule_id=recurrence_rule_id,
                competence_month=competence_month,
                scheduled_date=scheduled_date,
                status=RecurrenceOccurrenceStatus.PENDING,
                movement_id=None,
                blocked_reason_code=None,
                blocked_reason_message=None,
                failure_reason=None,
                attempt_count=0,
                processed_at=None,
                created_at=datetime.now(tz=UTC),
                updated_at=datetime.now(tz=UTC),
            )
            self._session.add(occurrence)
            try:
                self._session.flush()
                return occurrence, True
            except IntegrityError as exc:
                duplicate_error = exc

        existing = self.get_occurrence(
            recurrence_rule_id=recurrence_rule_id,
            competence_month=competence_month,
        )
        if existing is None:
            if duplicate_error is not None:
                raise duplicate_error
            msg = "Failed to load occurrence after idempotent insert attempt."
            raise RuntimeError(msg)
        return existing, False

    def get_generated_movement_by_external_id(
        self,
        *,
        competence_month: date,
        payer_participant_id: str,
        external_id: str,
    ) -> FinancialMovement | None:
        """Fetch one generated movement by deterministic external id."""

        statement = select(FinancialMovement).where(
            FinancialMovement.competence_month == competence_month,
            FinancialMovement.payer_participant_id == payer_participant_id,
            FinancialMovement.external_id == external_id,
            FinancialMovement.movement_type == MovementType.PURCHASE,
        )
        return self._session.scalar(statement)

    def add_generated_movement(
        self,
        *,
        amount: Decimal,
        description: str,
        competence_month: date,
        scheduled_date: date,
        payer_participant_id: str,
        requested_by_participant_id: str,
        external_id: str,
    ) -> FinancialMovement:
        """Create one purchase movement generated from recurrence rule."""

        movement = FinancialMovement(
            movement_type=MovementType.PURCHASE,
            amount=amount,
            description=description,
            occurred_at=datetime(
                year=scheduled_date.year,
                month=scheduled_date.month,
                day=scheduled_date.day,
                tzinfo=UTC,
            ),
            competence_month=competence_month,
            payer_participant_id=payer_participant_id,
            requested_by_participant_id=requested_by_participant_id,
            external_id=external_id,
            original_purchase_id=None,
        )
        self._session.add(movement)
        self._session.flush()
        return movement

    def add_event(
        self,
        *,
        recurrence_rule_id: UUID,
        event_type: RecurrenceEventType,
        payload: dict[str, Any],
        actor_participant_id: str | None = None,
        recurrence_occurrence_id: UUID | None = None,
    ) -> RecurrenceEvent:
        """Append one recurrence functional event."""

        event = RecurrenceEvent(
            recurrence_rule_id=recurrence_rule_id,
            recurrence_occurrence_id=recurrence_occurrence_id,
            event_type=event_type,
            actor_participant_id=actor_participant_id,
            payload=payload,
            created_at=datetime.now(tz=UTC),
        )
        self._session.add(event)
        self._session.flush()
        return event

    def update_rule_generation_cursor(
        self,
        *,
        recurrence_rule_id: UUID,
        processed_competence_month: date,
        next_competence_month: date,
    ) -> None:
        """Persist recurrence generation cursor updates."""

        rule = self.get_rule_for_update(recurrence_rule_id)
        if rule is None:
            return

        if rule.first_generated_competence_month is None:
            rule.first_generated_competence_month = processed_competence_month
        rule.last_generated_competence_month = processed_competence_month
        rule.next_competence_month = next_competence_month
        rule.version += 1

    def update_rule(
        self,
        *,
        rule: RecurrenceRule,
        description: str | None,
        amount: Decimal | None,
        payer_participant_id: str | None,
        requested_by_participant_id: str,
        split_config: dict[str, Any] | None,
        reference_day: int | None,
        start_competence_month: date | None,
        end_competence_month: date | None,
        clear_end_competence_month: bool,
    ) -> RecurrenceRule:
        """Update mutable recurrence fields using last-write-wins semantics."""

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
        rule.version += 1
        rule.updated_at = datetime.now(tz=UTC)
        self._session.flush()
        return rule

    def pause_rule(
        self,
        *,
        rule: RecurrenceRule,
    ) -> RecurrenceRule:
        """Pause one recurrence rule."""

        rule.status = RecurrenceStatus.PAUSED
        rule.version += 1
        rule.updated_at = datetime.now(tz=UTC)
        self._session.flush()
        return rule

    def reactivate_rule(
        self,
        *,
        rule: RecurrenceRule,
    ) -> RecurrenceRule:
        """Reactivate one paused recurrence rule."""

        rule.status = RecurrenceStatus.ACTIVE
        rule.version += 1
        rule.updated_at = datetime.now(tz=UTC)
        self._session.flush()
        return rule

    def end_rule(
        self,
        *,
        rule: RecurrenceRule,
        end_competence_month: date | None,
    ) -> RecurrenceRule:
        """Mark one recurrence rule as ended."""

        if end_competence_month is not None:
            rule.end_competence_month = end_competence_month
        rule.status = RecurrenceStatus.ENDED
        rule.version += 1
        rule.updated_at = datetime.now(tz=UTC)
        self._session.flush()
        return rule

    @staticmethod
    def _apply_list_filters(
        statement: Select[tuple[RecurrenceRule]],
        filters: RecurrenceListFilters,
    ) -> Select[tuple[RecurrenceRule]]:
        typed_statement = statement

        if filters.status is not None:
            typed_statement = typed_statement.where(
                RecurrenceRule.status == filters.status
            )

        if filters.competence_month is not None:
            typed_statement = typed_statement.where(
                RecurrenceRule.start_competence_month <= filters.competence_month,
                or_(
                    RecurrenceRule.end_competence_month.is_(None),
                    RecurrenceRule.end_competence_month >= filters.competence_month,
                ),
            )

        return typed_statement
