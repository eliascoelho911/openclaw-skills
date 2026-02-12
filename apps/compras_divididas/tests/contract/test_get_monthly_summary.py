from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from compras_divididas.api.app import create_app
from compras_divididas.db.models.participant import Participant
from compras_divididas.db.session import get_db_session


def seed_two_participants(session: Session) -> tuple[str, str]:
    participant_a = Participant(id="ana", display_name="Ana", is_active=True)
    participant_b = Participant(id="bia", display_name="Bia", is_active=True)
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


def test_get_monthly_summary_returns_200_with_contract_shape(
    client: TestClient, participants: tuple[str, str]
) -> None:
    participant_a, _ = participants
    assert (
        client.post(
            "/v1/movements",
            json={
                "type": "purchase",
                "amount": "100.00",
                "description": "Mercado",
                "occurred_at": "2026-02-10T12:00:00Z",
                "requested_by_participant_id": participant_a,
            },
        ).status_code
        == 201
    )

    response = client.get("/v1/months/2026/2/summary")
    assert response.status_code == 200

    body = response.json()
    assert body["competence_month"] == "2026-02"
    assert body["total_gross"] == "100.00"
    assert body["total_refunds"] == "0.00"
    assert body["total_net"] == "100.00"
    assert len(body["participants"]) == 2
    assert set(body["transfer"].keys()) == {
        "amount",
        "debtor_participant_id",
        "creditor_participant_id",
    }


def test_get_monthly_summary_returns_400_for_invalid_path_params(
    client: TestClient,
) -> None:
    response = client.get("/v1/months/2026/13/summary")

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"


def test_openapi_contains_monthly_summary_path() -> None:
    app = create_app()
    schema = app.openapi()
    get_operation = schema["paths"]["/v1/months/{year}/{month}/summary"]["get"]
    response_codes = set(get_operation["responses"].keys())

    assert "200" in response_codes
