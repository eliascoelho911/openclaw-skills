"""Integration tests for recurrence generation resume behavior."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from compras_divididas.db.models.financial_movement import FinancialMovement
from compras_divididas.db.models.recurrence_occurrence import (
    RecurrenceOccurrence,
    RecurrenceOccurrenceStatus,
)
from compras_divididas.db.models.recurrence_rule import RecurrenceRule


def test_generation_resume_after_partial_state_does_not_duplicate_movements(
    client: TestClient,
    participants: tuple[str, str],
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    participant_a, _ = participants
    create_response = client.post(
        "/v1/recurrences",
        json={
            "description": "Internet",
            "amount": "120.00",
            "payer_participant_id": participant_a,
            "requested_by_participant_id": participant_a,
            "split_config": {"mode": "equal"},
            "reference_day": 31,
            "start_competence_month": "2026-02",
        },
    )
    assert create_response.status_code == 201
    recurrence_id = UUID(create_response.json()["id"])

    first_generation = client.post("/v1/months/2026/2/recurrences/generate")
    assert first_generation.status_code == 200
    assert first_generation.json()["generated_count"] == 1

    with sqlite_session_factory() as session:
        occurrence = session.scalar(
            select(RecurrenceOccurrence).where(
                RecurrenceOccurrence.recurrence_rule_id == recurrence_id,
                RecurrenceOccurrence.competence_month == date(2026, 2, 1),
            )
        )
        assert occurrence is not None
        occurrence.status = RecurrenceOccurrenceStatus.PENDING
        occurrence.movement_id = None
        occurrence.processed_at = None

        rule = session.get(RecurrenceRule, recurrence_id)
        assert rule is not None
        rule.next_competence_month = date(2026, 2, 1)
        session.commit()

    resumed_generation = client.post("/v1/months/2026/2/recurrences/generate")
    assert resumed_generation.status_code == 200
    resumed_body = resumed_generation.json()
    assert resumed_body["generated_count"] == 1
    assert resumed_body["failed_count"] == 0

    with sqlite_session_factory() as session:
        movement_count = session.scalar(
            select(func.count()).select_from(FinancialMovement)
        )
        occurrence = session.scalar(
            select(RecurrenceOccurrence).where(
                RecurrenceOccurrence.recurrence_rule_id == recurrence_id,
                RecurrenceOccurrence.competence_month == date(2026, 2, 1),
            )
        )

    assert movement_count == 1
    assert occurrence is not None
    assert occurrence.status == RecurrenceOccurrenceStatus.GENERATED
