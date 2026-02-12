from __future__ import annotations

from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from compras_divididas.api.app import create_app
from compras_divididas.db.models.participant import Participant
from compras_divididas.db.models.recurrence_rule import (
    RecurrencePeriodicity,
    RecurrenceRule,
    RecurrenceStatus,
)
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


def test_list_recurrences_returns_filtered_paginated_response(
    client: TestClient,
    sqlite_session_factory: sessionmaker[Session],
    participants: tuple[str, str],
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
            "reference_day": 10,
            "start_competence_month": "2026-02",
        },
    )
    assert create_response.status_code == 201

    with sqlite_session_factory() as session:
        session.add(
            RecurrenceRule(
                description="Plano anual",
                amount=Decimal("55.00"),
                payer_participant_id=participant_a,
                requested_by_participant_id=participant_a,
                split_config={"mode": "equal"},
                periodicity=RecurrencePeriodicity.MONTHLY,
                reference_day=5,
                start_competence_month=date(2025, 1, 1),
                end_competence_month=date(2025, 12, 1),
                status=RecurrenceStatus.ENDED,
                first_generated_competence_month=None,
                last_generated_competence_month=None,
                next_competence_month=date(2025, 12, 1),
                version=1,
            )
        )
        session.commit()

    response = client.get(
        "/v1/recurrences",
        params={"status": "active", "year": 2026, "month": 2, "limit": 10, "offset": 0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 10
    assert body["offset"] == 0
    assert len(body["items"]) == 1
    assert body["items"][0]["status"] == "active"
    assert body["items"][0]["next_competence_month"] == "2026-02"


def test_list_recurrences_returns_400_when_year_or_month_is_missing(
    client: TestClient,
) -> None:
    response = client.get("/v1/recurrences", params={"year": 2026})

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"


def test_openapi_for_list_recurrences_contains_contract_response_codes() -> None:
    app = create_app()
    schema = app.openapi()
    get_operation = schema["paths"]["/v1/recurrences"]["get"]
    response_codes = set(get_operation["responses"].keys())

    assert {"200", "400"}.issubset(response_codes)
