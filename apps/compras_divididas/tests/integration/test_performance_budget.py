from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from time import perf_counter

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from compras_divididas.api.app import create_app
from compras_divididas.db.models.financial_movement import (
    FinancialMovement,
    MovementType,
)
from compras_divididas.db.models.participant import Participant
from compras_divididas.db.session import get_db_session

MONTHLY_DATASET_SIZE = 5_000
PR001_P95_SECONDS = 2.0
PR002_SECONDS = 3.0
PR003_SECONDS = 5.0


def _seed_two_participants(session: Session) -> tuple[str, str]:
    participant_a = Participant(id="ana", display_name="Ana", is_active=True)
    participant_b = Participant(id="bia", display_name="Bia", is_active=True)
    session.add_all([participant_a, participant_b])
    session.commit()
    return participant_a.id, participant_b.id


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


def _p95(latencies: list[float]) -> float:
    ordered = sorted(latencies)
    index = int(len(ordered) * 0.95) - 1
    return ordered[max(index, 0)]


@pytest.fixture
def client(
    sqlite_session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db_session() -> Generator[Session, None, None]:
        with sqlite_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def participants(sqlite_session_factory: sessionmaker[Session]) -> tuple[str, str]:
    with sqlite_session_factory() as session:
        participant_a, participant_b = _seed_two_participants(session)
    return participant_a, participant_b


@pytest.fixture
def populated_month(
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
    populated_month: None,
) -> None:
    _ = populated_month
    start = perf_counter()
    response = client.get("/v1/months/2026/2/summary")
    elapsed = perf_counter() - start

    assert response.status_code == 200
    assert elapsed <= PR002_SECONDS


def test_monthly_report_under_budget_pr003(
    client: TestClient,
    populated_month: None,
) -> None:
    _ = populated_month
    start = perf_counter()
    response = client.get("/v1/months/2026/2/report")
    elapsed = perf_counter() - start

    assert response.status_code == 200
    assert elapsed <= PR003_SECONDS
