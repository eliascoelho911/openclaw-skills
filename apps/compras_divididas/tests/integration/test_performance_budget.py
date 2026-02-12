from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from time import perf_counter

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from compras_divididas.db.models.financial_movement import (
    FinancialMovement,
    MovementType,
)
from compras_divididas.db.models.recurrence_rule import (
    RecurrencePeriodicity,
    RecurrenceRule,
    RecurrenceStatus,
)

MONTHLY_DATASET_SIZE = 5_000
RECURRENCE_ELIGIBLE_DATASET_SIZE = 1_000
PR001_P95_SECONDS = 2.0
PR002_GENERATION_SECONDS = 30.0
SUMMARY_SECONDS = 3.0
PR003_SECONDS = 5.0


def _seed_monthly_dataset(
    session: Session,
    *,
    participant_a_id: str,
    participant_b_id: str,
) -> None:
    participant_ids = [participant_a_id, participant_b_id]
    movements = [
        FinancialMovement(
            movement_type=MovementType.PURCHASE,
            amount=Decimal("10.00"),
            description=f"Load purchase {index}",
            occurred_at=datetime(2026, 2, (index % 28) + 1, 12, 0, tzinfo=UTC),
            competence_month=datetime(2026, 2, 1, tzinfo=UTC).date(),
            payer_participant_id=participant_ids[index % 2],
            requested_by_participant_id=participant_ids[index % 2],
            external_id=f"perf-{index}",
        )
        for index in range(MONTHLY_DATASET_SIZE)
    ]
    session.add_all(movements)
    session.commit()


def _seed_recurrence_dataset(session: Session, *, participant_id: str) -> None:
    rules = [
        RecurrenceRule(
            description=f"Recurring charge {index}",
            amount=Decimal("10.00"),
            payer_participant_id=participant_id,
            requested_by_participant_id=participant_id,
            split_config={"mode": "equal"},
            periodicity=RecurrencePeriodicity.MONTHLY,
            reference_day=((index % 28) + 1),
            start_competence_month=date(2026, 2, 1),
            end_competence_month=None,
            status=RecurrenceStatus.ACTIVE,
            first_generated_competence_month=None,
            last_generated_competence_month=None,
            next_competence_month=date(2026, 2, 1),
        )
        for index in range(RECURRENCE_ELIGIBLE_DATASET_SIZE)
    ]
    session.add_all(rules)
    session.commit()


def _p95(latencies: list[float]) -> float:
    ordered = sorted(latencies)
    index = int(len(ordered) * 0.95) - 1
    return ordered[max(index, 0)]


def _seed_populated_month(
    sqlite_session_factory: sessionmaker[Session],
    participants: tuple[str, str],
) -> None:
    participant_a, participant_b = participants
    with sqlite_session_factory() as session:
        _seed_monthly_dataset(
            session,
            participant_a_id=participant_a,
            participant_b_id=participant_b,
        )


def _seed_eligible_recurrences(
    sqlite_session_factory: sessionmaker[Session],
    participants: tuple[str, str],
) -> None:
    participant_a, _ = participants
    with sqlite_session_factory() as session:
        _seed_recurrence_dataset(session, participant_id=participant_a)


def test_purchase_registration_p95_under_budget_pr001(
    client: TestClient,
    participants: tuple[str, str],
) -> None:
    participant_a, _ = participants
    latencies: list[float] = []

    for index in range(20):
        payload = {
            "type": "purchase",
            "amount": "25.90",
            "description": f"Load request {index}",
            "occurred_at": "2026-03-10T12:00:00Z",
            "requested_by_participant_id": participant_a,
            "external_id": f"pr001-{index}",
        }
        start = perf_counter()
        response = client.post("/v1/movements", json=payload)
        latency = perf_counter() - start
        latencies.append(latency)
        assert response.status_code == 201

    assert _p95(latencies) <= PR001_P95_SECONDS


def test_monthly_summary_under_budget_pr002(
    client: TestClient,
    sqlite_session_factory: sessionmaker[Session],
    participants: tuple[str, str],
) -> None:
    _seed_populated_month(sqlite_session_factory, participants)
    start = perf_counter()
    response = client.get("/v1/months/2026/2/summary")
    elapsed = perf_counter() - start

    assert response.status_code == 200
    assert elapsed <= SUMMARY_SECONDS


def test_monthly_report_under_budget_pr003(
    client: TestClient,
    sqlite_session_factory: sessionmaker[Session],
    participants: tuple[str, str],
) -> None:
    _seed_populated_month(sqlite_session_factory, participants)
    start = perf_counter()
    response = client.get("/v1/months/2026/2/report")
    elapsed = perf_counter() - start

    assert response.status_code == 200
    assert elapsed <= PR003_SECONDS


def test_recurrence_generation_1000_eligible_rules_under_budget_pr002(
    client: TestClient,
    sqlite_session_factory: sessionmaker[Session],
    participants: tuple[str, str],
) -> None:
    _seed_eligible_recurrences(sqlite_session_factory, participants)

    processed_rules_total = 0
    generated_count_total = 0
    ignored_count_total = 0
    blocked_count_total = 0
    failed_count_total = 0

    start = perf_counter()
    while processed_rules_total < RECURRENCE_ELIGIBLE_DATASET_SIZE:
        response = client.post("/v1/months/2026/2/recurrences/generate")
        assert response.status_code == 200
        body = response.json()

        processed_batch = body["processed_rules"]
        if processed_batch == 0:
            break

        processed_rules_total += processed_batch
        generated_count_total += body["generated_count"]
        ignored_count_total += body["ignored_count"]
        blocked_count_total += body["blocked_count"]
        failed_count_total += body["failed_count"]

    elapsed = perf_counter() - start

    assert processed_rules_total == RECURRENCE_ELIGIBLE_DATASET_SIZE
    assert generated_count_total == RECURRENCE_ELIGIBLE_DATASET_SIZE
    assert ignored_count_total == 0
    assert blocked_count_total == 0
    assert failed_count_total == 0
    assert elapsed <= PR002_GENERATION_SECONDS
