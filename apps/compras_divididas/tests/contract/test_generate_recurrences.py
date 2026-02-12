"""Contract tests for monthly recurrence generation endpoint."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from compras_divididas.api.app import create_app
from compras_divididas.db.models.financial_movement import FinancialMovement
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


def test_generate_recurrences_returns_counters_and_is_idempotent(
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

    first_generation = client.post("/v1/months/2026/2/recurrences/generate")
    assert first_generation.status_code == 200
    first_body = first_generation.json()
    assert first_body["competence_month"] == "2026-02"
    assert first_body["generated_count"] == 1
    assert first_body["ignored_count"] == 0
    assert first_body["blocked_count"] == 0
    assert first_body["failed_count"] == 0

    second_generation = client.post("/v1/months/2026/2/recurrences/generate")
    assert second_generation.status_code == 200
    second_body = second_generation.json()
    assert second_body["generated_count"] == 0
    assert second_body["blocked_count"] == 0
    assert second_body["failed_count"] == 0

    with sqlite_session_factory() as session:
        movement_count = session.scalar(
            select(func.count()).select_from(FinancialMovement)
        )
    assert movement_count == 1


def test_openapi_contains_generate_recurrences_path() -> None:
    app = create_app()
    schema = app.openapi()
    post_operation = schema["paths"]["/v1/months/{year}/{month}/recurrences/generate"][
        "post"
    ]
    response_codes = set(post_operation["responses"].keys())

    assert "200" in response_codes
