"""Contract tests for recurrence creation endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from compras_divididas.api.app import create_app


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
