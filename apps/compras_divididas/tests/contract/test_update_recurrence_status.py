"""Contract tests for recurrence lifecycle status endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


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
    return str(response.json()["id"])


def test_pause_reactivate_and_end_transitions(
    client: TestClient,
    participants: tuple[str, str],
) -> None:
    participant_a, _ = participants
    recurrence_id = _create_recurrence(client, participant_a)

    pause_response = client.post(
        f"/v1/recurrences/{recurrence_id}/pause",
        json={
            "requested_by_participant_id": participant_a,
            "reason": "Temporary stop",
        },
    )
    assert pause_response.status_code == 200
    assert pause_response.json()["status"] == "paused"

    reactivate_response = client.post(
        f"/v1/recurrences/{recurrence_id}/reactivate",
        json={"requested_by_participant_id": participant_a},
    )
    assert reactivate_response.status_code == 200
    assert reactivate_response.json()["status"] == "active"

    end_response = client.post(
        f"/v1/recurrences/{recurrence_id}/end",
        json={
            "requested_by_participant_id": participant_a,
            "end_competence_month": "2026-12",
        },
    )
    assert end_response.status_code == 200
    assert end_response.json()["status"] == "ended"


def test_pause_rejects_invalid_transition_from_paused(
    client: TestClient,
    participants: tuple[str, str],
) -> None:
    participant_a, _ = participants
    recurrence_id = _create_recurrence(client, participant_a)

    first_pause = client.post(
        f"/v1/recurrences/{recurrence_id}/pause",
        json={"requested_by_participant_id": participant_a},
    )
    assert first_pause.status_code == 200

    second_pause = client.post(
        f"/v1/recurrences/{recurrence_id}/pause",
        json={"requested_by_participant_id": participant_a},
    )
    assert second_pause.status_code == 422
    assert second_pause.json()["code"] == "INVALID_RECURRENCE_STATE_TRANSITION"
