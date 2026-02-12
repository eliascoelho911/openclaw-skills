"""Recurrence generation service orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol
from uuid import UUID

from compras_divididas.db.models.recurrence_event import RecurrenceEventType
from compras_divididas.db.models.recurrence_occurrence import (
    RecurrenceOccurrence,
    RecurrenceOccurrenceStatus,
)
from compras_divididas.db.models.recurrence_rule import RecurrenceRule
from compras_divididas.domain.recurrence_schedule import (
    add_months,
    scheduled_date_for_month,
)
from compras_divididas.repositories.recurrence_repository import (
    EligibleRecurrenceRuleFilters,
    RecurrenceRepository,
)


@dataclass(slots=True, frozen=True)
class BlockedRecurrenceItem:
    """Blocked recurrence metadata returned by generation endpoint."""

    recurrence_id: UUID
    code: str
    message: str


@dataclass(slots=True, frozen=True)
class GenerateRecurrencesResult:
    """Result counters for one recurrence generation run."""

    competence_month: date
    processed_rules: int
    generated_count: int
    ignored_count: int
    blocked_count: int
    failed_count: int
    blocked_items: list[BlockedRecurrenceItem]


class SessionProtocol(Protocol):
    """Subset of SQLAlchemy session APIs used by generation service."""

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class RecurrenceGenerationService:
    """Coordinates monthly recurrence generation workflows."""

    def __init__(
        self,
        *,
        recurrence_repository: RecurrenceRepository,
        session: SessionProtocol,
    ) -> None:
        self._recurrence_repository = recurrence_repository
        self._session = session

    def generate_for_month(
        self,
        *,
        competence_month: date,
        requested_by_participant_id: str | None,
        include_blocked_details: bool,
        dry_run: bool,
    ) -> GenerateRecurrencesResult:
        """Generate recurrence occurrences idempotently for one month."""

        generated_count = 0
        ignored_count = 0
        blocked_count = 0
        failed_count = 0
        blocked_items: list[BlockedRecurrenceItem] = []
        processed_rules = 0

        rules = self._recurrence_repository.list_eligible_rules_for_generation(
            EligibleRecurrenceRuleFilters(competence_month=competence_month)
        )
        for rule in rules:
            processed_rules += 1
            try:
                status, blocked = self._process_rule(
                    rule=rule,
                    competence_month=competence_month,
                    requested_by_participant_id=requested_by_participant_id,
                    dry_run=dry_run,
                )
            except Exception:
                failed_count += 1
                self._session.rollback()
                continue

            if status == "generated":
                generated_count += 1
            elif status == "ignored":
                ignored_count += 1
            elif status == "blocked":
                blocked_count += 1
                if include_blocked_details and blocked is not None:
                    blocked_items.append(blocked)
            elif status == "failed":
                failed_count += 1

        return GenerateRecurrencesResult(
            competence_month=competence_month,
            processed_rules=processed_rules,
            generated_count=generated_count,
            ignored_count=ignored_count,
            blocked_count=blocked_count,
            failed_count=failed_count,
            blocked_items=blocked_items,
        )

    def _process_rule(
        self,
        *,
        rule: RecurrenceRule,
        competence_month: date,
        requested_by_participant_id: str | None,
        dry_run: bool,
    ) -> tuple[str, BlockedRecurrenceItem | None]:
        scheduled_date = scheduled_date_for_month(
            competence_month=competence_month,
            reference_day=rule.reference_day,
        )
        occurrence, created = (
            self._recurrence_repository.create_pending_occurrence_if_missing(
                recurrence_rule_id=rule.id,
                competence_month=competence_month,
                scheduled_date=scheduled_date,
            )
        )

        if not created and occurrence.status == RecurrenceOccurrenceStatus.GENERATED:
            self._recurrence_repository.add_event(
                recurrence_rule_id=rule.id,
                recurrence_occurrence_id=occurrence.id,
                event_type=RecurrenceEventType.RECURRENCE_IGNORED,
                actor_participant_id=requested_by_participant_id,
                payload={
                    "reason": "already_generated",
                    "competence_month": competence_month.isoformat(),
                },
            )
            self._session.commit()
            return "ignored", None

        blocked = self._build_blocked_item(rule)
        if blocked is not None:
            self._mark_occurrence_blocked(occurrence=occurrence, blocked=blocked)
            self._recurrence_repository.add_event(
                recurrence_rule_id=rule.id,
                recurrence_occurrence_id=occurrence.id,
                event_type=RecurrenceEventType.RECURRENCE_BLOCKED,
                actor_participant_id=requested_by_participant_id,
                payload={
                    "code": blocked.code,
                    "message": blocked.message,
                    "competence_month": competence_month.isoformat(),
                },
            )
            self._session.commit()
            return "blocked", blocked

        external_id = (
            f"recurrence:{rule.id}:{competence_month.year:04d}-"
            f"{competence_month.month:02d}"
        )
        movement = self._recurrence_repository.get_generated_movement_by_external_id(
            competence_month=competence_month,
            payer_participant_id=rule.payer_participant_id,
            external_id=external_id,
        )
        if movement is None and not dry_run:
            movement = self._recurrence_repository.add_generated_movement(
                amount=rule.amount,
                description=rule.description,
                competence_month=competence_month,
                scheduled_date=scheduled_date,
                payer_participant_id=rule.payer_participant_id,
                requested_by_participant_id=rule.requested_by_participant_id,
                external_id=external_id,
            )

        if dry_run:
            self._recurrence_repository.add_event(
                recurrence_rule_id=rule.id,
                recurrence_occurrence_id=occurrence.id,
                event_type=RecurrenceEventType.RECURRENCE_IGNORED,
                actor_participant_id=requested_by_participant_id,
                payload={
                    "reason": "dry_run",
                    "competence_month": competence_month.isoformat(),
                },
            )
            self._session.commit()
            return "ignored", None

        if movement is None:
            self._mark_occurrence_failed(
                occurrence=occurrence,
                reason="Failed to create movement for recurrence generation.",
            )
            self._session.commit()
            return "failed", None

        self._mark_occurrence_generated(occurrence=occurrence, movement_id=movement.id)
        self._recurrence_repository.update_rule_generation_cursor(
            recurrence_rule_id=rule.id,
            processed_competence_month=competence_month,
            next_competence_month=add_months(competence_month, 1),
        )
        self._recurrence_repository.add_event(
            recurrence_rule_id=rule.id,
            recurrence_occurrence_id=occurrence.id,
            event_type=RecurrenceEventType.RECURRENCE_GENERATED,
            actor_participant_id=requested_by_participant_id,
            payload={
                "movement_id": str(movement.id),
                "competence_month": competence_month.isoformat(),
            },
        )
        self._session.commit()
        return "generated", None

    def _build_blocked_item(self, rule: RecurrenceRule) -> BlockedRecurrenceItem | None:
        if str(rule.split_config.get("mode", "")).strip() != "equal":
            return BlockedRecurrenceItem(
                recurrence_id=rule.id,
                code="INVALID_SPLIT_CONFIG",
                message=(
                    "Cause: split_config.mode is not supported for recurrence "
                    "generation. "
                    "Action: Update recurrence split_config.mode to equal and retry."
                ),
            )
        return None

    @staticmethod
    def _mark_occurrence_generated(
        *,
        occurrence: RecurrenceOccurrence,
        movement_id: UUID,
    ) -> None:
        occurrence.status = RecurrenceOccurrenceStatus.GENERATED
        occurrence.movement_id = movement_id
        occurrence.blocked_reason_code = None
        occurrence.blocked_reason_message = None
        occurrence.failure_reason = None
        occurrence.attempt_count += 1
        occurrence.processed_at = datetime.now(tz=UTC)

    @staticmethod
    def _mark_occurrence_blocked(
        *,
        occurrence: RecurrenceOccurrence,
        blocked: BlockedRecurrenceItem,
    ) -> None:
        occurrence.status = RecurrenceOccurrenceStatus.BLOCKED
        occurrence.movement_id = None
        occurrence.blocked_reason_code = blocked.code
        occurrence.blocked_reason_message = blocked.message
        occurrence.failure_reason = None
        occurrence.attempt_count += 1
        occurrence.processed_at = datetime.now(tz=UTC)

    @staticmethod
    def _mark_occurrence_failed(
        *, occurrence: RecurrenceOccurrence, reason: str
    ) -> None:
        occurrence.status = RecurrenceOccurrenceStatus.FAILED
        occurrence.movement_id = None
        occurrence.blocked_reason_code = None
        occurrence.blocked_reason_message = None
        occurrence.failure_reason = reason
        occurrence.attempt_count += 1
        occurrence.processed_at = datetime.now(tz=UTC)
