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


def test_create_and_list_recurrence_flow(
    client: TestClient,
    participants: tuple[str, str],
) -> None:
    participant_a, _ = participants
    create_response = client.post(
        "/v1/recurrences",
        json={
            "description": "Internet residencial",
            "amount": "120.00",
            "payer_participant_id": participant_a,
            "requested_by_participant_id": participant_a,
            "split_config": {"mode": "equal"},
            "reference_day": 31,
            "start_competence_month": "2026-02",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] == "active"
    assert created["next_competence_month"] == "2026-02"

    list_response = client.get(
        "/v1/recurrences",
        params={"status": "active", "year": 2026, "month": 2},
    )

    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == created["id"]
    assert body["items"][0]["description"] == "Internet residencial"
