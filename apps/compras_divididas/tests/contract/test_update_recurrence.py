"""Contract tests for recurrence update endpoint."""

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


def _create_recurrence(client: TestClient, participant_id: str) -> str:
    response = client.post(
        "/v1/recurrences",
        json={
            "description": "Internet",
            "amount": "120.00",
            "payer_participant_id": participant_id,
            "requested_by_participant_id": participant_id,
            "split_config": {"mode": "equal"},
            "reference_day": 31,
            "start_competence_month": "2026-02",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_patch_recurrence_updates_fields(
    client: TestClient,
    participants: tuple[str, str],
) -> None:
    participant_a, participant_b = participants
    recurrence_id = _create_recurrence(client, participant_a)

    response = client.patch(
        f"/v1/recurrences/{recurrence_id}",
        json={
            "requested_by_participant_id": participant_a,
            "description": "Internet fibra",
            "amount": "139.90",
            "payer_participant_id": participant_b,
            "reference_day": 15,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Internet fibra"
    assert body["amount"] == "139.90"
    assert body["payer_participant_id"] == participant_b
    assert body["reference_day"] == 15


def test_patch_recurrence_locks_start_competence_after_generation(
    client: TestClient,
    participants: tuple[str, str],
) -> None:
    participant_a, _ = participants
    recurrence_id = _create_recurrence(client, participant_a)
    generation_response = client.post("/v1/months/2026/2/recurrences/generate")
    assert generation_response.status_code == 200

    response = client.patch(
        f"/v1/recurrences/{recurrence_id}",
        json={
            "requested_by_participant_id": participant_a,
            "start_competence_month": "2026-01",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "START_COMPETENCE_LOCKED"
