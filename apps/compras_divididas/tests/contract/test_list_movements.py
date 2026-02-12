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


def test_list_movements_filters_and_pagination(
    client: TestClient, participants: tuple[str, str]
) -> None:
    participant_a, participant_b = participants

    feb_payload_1 = {
        "type": "purchase",
        "amount": "120.00",
        "description": "Supermercado",
        "occurred_at": "2026-02-10T12:00:00Z",
        "requested_by_participant_id": participant_a,
        "external_id": "wpp-101",
    }
    feb_payload_2 = {
        "type": "purchase",
        "amount": "40.00",
        "description": "Farmacia",
        "occurred_at": "2026-02-15T12:00:00Z",
        "requested_by_participant_id": participant_b,
        "external_id": "wpp-102",
    }
    mar_payload = {
        "type": "purchase",
        "amount": "70.00",
        "description": "Pet shop",
        "occurred_at": "2026-03-01T12:00:00Z",
        "requested_by_participant_id": participant_a,
        "external_id": "wpp-103",
    }

    assert client.post("/v1/movements", json=feb_payload_1).status_code == 201
    assert client.post("/v1/movements", json=feb_payload_2).status_code == 201
    assert client.post("/v1/movements", json=mar_payload).status_code == 201

    response = client.get("/v1/movements", params={"year": 2026, "month": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert len(body["items"]) == 2

    filtered_response = client.get(
        "/v1/movements",
        params={
            "year": 2026,
            "month": 2,
            "type": "purchase",
            "description": "super",
            "amount": "120.00",
            "participant_id": participant_a,
            "external_id": "wpp-101",
            "limit": 1,
            "offset": 0,
        },
    )
    assert filtered_response.status_code == 200
    filtered_body = filtered_response.json()
    assert filtered_body["total"] == 1
    assert filtered_body["limit"] == 1
    assert filtered_body["offset"] == 0
    assert len(filtered_body["items"]) == 1
    assert filtered_body["items"][0]["description"] == "Supermercado"
    assert filtered_body["items"][0]["external_id"] == "wpp-101"


def test_list_movements_returns_400_for_missing_required_filters(
    client: TestClient,
) -> None:
    response = client.get("/v1/movements", params={"year": 2026})

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"


def test_openapi_for_list_movements_contains_required_parameters() -> None:
    app = create_app()
    schema = app.openapi()
    get_operation = schema["paths"]["/v1/movements"]["get"]
    parameters = get_operation["parameters"]
    by_name = {parameter["name"]: parameter for parameter in parameters}

    assert by_name["year"]["required"] is True
    assert by_name["month"]["required"] is True
    assert "200" in get_operation["responses"]
    assert "400" in get_operation["responses"]
