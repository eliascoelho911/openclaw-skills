from __future__ import annotations

from collections.abc import Generator
from uuid import uuid4

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


def test_create_movement_returns_201(
    client: TestClient, participants: tuple[str, str]
) -> None:
    participant_a, _ = participants
    response = client.post(
        "/v1/movements",
        json={
            "type": "purchase",
            "amount": "10.00",
            "description": "Padaria",
            "requested_by_participant_id": participant_a,
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["type"] == "purchase"
    assert body["amount"] == "10.00"
    assert body["description"] == "Padaria"
    assert body["payer_participant_id"] == participant_a
    assert body["requested_by_participant_id"] == participant_a


def test_create_movement_returns_400_for_invalid_payload(
    client: TestClient, participants: tuple[str, str]
) -> None:
    participant_a, _ = participants
    response = client.post(
        "/v1/movements",
        json={
            "type": "purchase",
            "amount": "0.00",
            "description": "Padaria",
            "requested_by_participant_id": participant_a,
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"


def test_create_movement_returns_404_when_refund_purchase_not_found(
    client: TestClient, participants: tuple[str, str]
) -> None:
    participant_a, _ = participants
    response = client.post(
        "/v1/movements",
        json={
            "type": "refund",
            "amount": "5.00",
            "description": "Estorno",
            "requested_by_participant_id": participant_a,
            "original_purchase_id": str(uuid4()),
        },
    )

    assert response.status_code == 404
    assert response.json()["code"] == "PURCHASE_NOT_FOUND"


def test_create_movement_returns_409_for_duplicate_external_id(
    client: TestClient, participants: tuple[str, str]
) -> None:
    participant_a, _ = participants

    payload = {
        "type": "purchase",
        "amount": "12.00",
        "description": "Mercado",
        "requested_by_participant_id": participant_a,
        "external_id": "wpp-001",
    }
    first_response = client.post("/v1/movements", json=payload)
    duplicate_response = client.post("/v1/movements", json=payload)

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["code"] == "DUPLICATE_EXTERNAL_ID"


def test_create_movement_returns_422_for_refund_limit_exceeded(
    client: TestClient, participants: tuple[str, str]
) -> None:
    participant_a, _ = participants

    purchase_response = client.post(
        "/v1/movements",
        json={
            "type": "purchase",
            "amount": "15.00",
            "description": "Farmacia",
            "requested_by_participant_id": participant_a,
            "external_id": "wpp-002",
        },
    )
    assert purchase_response.status_code == 201

    refund_response = client.post(
        "/v1/movements",
        json={
            "type": "refund",
            "amount": "16.00",
            "description": "Cancelamento",
            "requested_by_participant_id": participant_a,
            "original_purchase_external_id": "wpp-002",
        },
    )

    assert refund_response.status_code == 422
    assert refund_response.json()["code"] == "REFUND_LIMIT_EXCEEDED"


def test_openapi_for_create_movement_contains_contract_response_codes() -> None:
    app = create_app()
    schema = app.openapi()
    post_operation = schema["paths"]["/v1/movements"]["post"]
    response_codes = set(post_operation["responses"].keys())

    assert {"201", "400", "404", "409", "422"}.issubset(response_codes)
