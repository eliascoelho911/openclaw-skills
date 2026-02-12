"""Contract tests for recurrence creation endpoint."""

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


def test_create_recurrence_returns_201(
    client: TestClient, participants: tuple[str, str]
) -> None:
    participant_a, _ = participants
    response = client.post(
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

    assert response.status_code == 201
    body = response.json()
    assert body["description"] == "Internet"
    assert body["amount"] == "120.00"
    assert body["status"] == "active"
    assert body["next_competence_month"] == "2026-02"


def test_create_recurrence_returns_400_for_invalid_payload(
    client: TestClient, participants: tuple[str, str]
) -> None:
    participant_a, _ = participants
    response = client.post(
        "/v1/recurrences",
        json={
            "description": "Internet",
            "amount": "120.00",
            "payer_participant_id": participant_a,
            "requested_by_participant_id": participant_a,
            "split_config": {"mode": "equal"},
            "reference_day": 0,
            "start_competence_month": "2026-02",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"


def test_create_recurrence_returns_422_for_unsupported_split_mode(
    client: TestClient, participants: tuple[str, str]
) -> None:
    participant_a, _ = participants
    response = client.post(
        "/v1/recurrences",
        json={
            "description": "Internet",
            "amount": "120.00",
            "payer_participant_id": participant_a,
            "requested_by_participant_id": participant_a,
            "split_config": {"mode": "weighted"},
            "reference_day": 15,
            "start_competence_month": "2026-02",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "DOMAIN_INVARIANT_VIOLATION"


def test_openapi_for_create_recurrence_contains_contract_response_codes() -> None:
    app = create_app()
    schema = app.openapi()
    post_operation = schema["paths"]["/v1/recurrences"]["post"]
    response_codes = set(post_operation["responses"].keys())

    assert {"201", "400", "422"}.issubset(response_codes)
