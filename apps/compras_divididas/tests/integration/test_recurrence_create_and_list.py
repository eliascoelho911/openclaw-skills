from __future__ import annotations

from fastapi.testclient import TestClient


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
