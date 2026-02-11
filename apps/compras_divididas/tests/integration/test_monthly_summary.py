from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from compras_divididas.api.app import create_app
from compras_divididas.db.models.participant import Participant
from compras_divididas.db.session import get_db_session


def seed_two_participants(session: Session) -> tuple[str, str]:
    participant_a = Participant(code="ana", display_name="Ana", is_active=True)
    participant_b = Participant(code="bia", display_name="Bia", is_active=True)
    session.add_all([participant_a, participant_b])
    session.commit()
    return str(participant_a.id), str(participant_b.id)


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
        participant_a, participant_b = seed_two_participants(session)
    return participant_a, participant_b


def test_monthly_summary_returns_zeroed_values_for_empty_month(
    client: TestClient, participants: tuple[str, str]
) -> None:
    participant_a, participant_b = participants

    response = client.get("/v1/months/2026/2/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_gross"] == "0.00"
    assert body["total_refunds"] == "0.00"
    assert body["total_net"] == "0.00"

    balances = {item["participant_id"]: item for item in body["participants"]}
    assert balances[participant_a]["paid_total"] == "0.00"
    assert balances[participant_b]["paid_total"] == "0.00"
    assert body["transfer"]["amount"] == "0.00"
    assert body["transfer"]["debtor_participant_id"] is None
    assert body["transfer"]["creditor_participant_id"] is None


def test_monthly_summary_returns_expected_totals_for_populated_month(
    client: TestClient, participants: tuple[str, str]
) -> None:
    participant_a, participant_b = participants

    assert (
        client.post(
            "/v1/movements",
            json={
                "type": "purchase",
                "amount": "100.00",
                "description": "Supermercado",
                "occurred_at": "2026-02-10T12:00:00Z",
                "requested_by_participant_id": participant_a,
                "external_id": "wpp-201",
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/v1/movements",
            json={
                "type": "purchase",
                "amount": "40.00",
                "description": "Padaria",
                "occurred_at": "2026-02-11T12:00:00Z",
                "requested_by_participant_id": participant_b,
                "external_id": "wpp-202",
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/v1/movements",
            json={
                "type": "refund",
                "amount": "20.00",
                "description": "Estorno parcial",
                "occurred_at": "2026-02-12T12:00:00Z",
                "requested_by_participant_id": participant_a,
                "original_purchase_external_id": "wpp-201",
            },
        ).status_code
        == 201
    )

    response = client.get("/v1/months/2026/2/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["competence_month"] == "2026-02"
    assert body["total_gross"] == "140.00"
    assert body["total_refunds"] == "20.00"
    assert body["total_net"] == "120.00"

    balances = {item["participant_id"]: item for item in body["participants"]}
    assert balances[participant_a]["paid_total"] == "80.00"
    assert balances[participant_b]["paid_total"] == "40.00"
    assert balances[participant_a]["share_due"] == "60.00"
    assert balances[participant_b]["share_due"] == "60.00"
    assert balances[participant_a]["net_balance"] == "20.00"
    assert balances[participant_b]["net_balance"] == "-20.00"

    assert body["transfer"]["amount"] == "20.00"
    assert body["transfer"]["debtor_participant_id"] == participant_b
    assert body["transfer"]["creditor_participant_id"] == participant_a
