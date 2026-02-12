from __future__ import annotations

from fastapi.testclient import TestClient


def test_monthly_summary_returns_zeroed_values_for_empty_month(
    client: TestClient, participants: tuple[str, str]
) -> None:
    participant_a, participant_b = participants

    response = client.get("/v1/months/2026/2/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_gross"] == "0.00"
    assert body["total_refunds"] == "0.00"
    assert body["total_net"] == "0.00"

    balances = {item["participant_id"]: item for item in body["participants"]}
    assert balances[participant_a]["paid_total"] == "0.00"
    assert balances[participant_b]["paid_total"] == "0.00"
    assert body["transfer"]["amount"] == "0.00"
    assert body["transfer"]["debtor_participant_id"] is None
    assert body["transfer"]["creditor_participant_id"] is None


def test_monthly_summary_returns_expected_totals_for_populated_month(
    client: TestClient, participants: tuple[str, str]
) -> None:
    participant_a, participant_b = participants

    assert (
        client.post(
            "/v1/movements",
            json={
                "type": "purchase",
                "amount": "100.00",
                "description": "Supermercado",
                "occurred_at": "2026-02-10T12:00:00Z",
                "requested_by_participant_id": participant_a,
                "external_id": "wpp-201",
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/v1/movements",
            json={
                "type": "purchase",
                "amount": "40.00",
                "description": "Padaria",
                "occurred_at": "2026-02-11T12:00:00Z",
                "requested_by_participant_id": participant_b,
                "external_id": "wpp-202",
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/v1/movements",
            json={
                "type": "refund",
                "amount": "20.00",
                "description": "Estorno parcial",
                "occurred_at": "2026-02-12T12:00:00Z",
                "requested_by_participant_id": participant_a,
                "original_purchase_external_id": "wpp-201",
            },
        ).status_code
        == 201
    )

    response = client.get("/v1/months/2026/2/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["competence_month"] == "2026-02"
    assert body["total_gross"] == "140.00"
    assert body["total_refunds"] == "20.00"
    assert body["total_net"] == "120.00"

    balances = {item["participant_id"]: item for item in body["participants"]}
    assert balances[participant_a]["paid_total"] == "80.00"
    assert balances[participant_b]["paid_total"] == "40.00"
    assert balances[participant_a]["share_due"] == "60.00"
    assert balances[participant_b]["share_due"] == "60.00"
    assert balances[participant_a]["net_balance"] == "20.00"
    assert balances[participant_b]["net_balance"] == "-20.00"

    assert body["transfer"]["amount"] == "20.00"
    assert body["transfer"]["debtor_participant_id"] == participant_b
    assert body["transfer"]["creditor_participant_id"] == participant_a


def test_monthly_summary_auto_generate_is_idempotent(
    client: TestClient, participants: tuple[str, str]
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

    first_response = client.get("/v1/months/2026/2/summary?auto_generate=true")
    assert first_response.status_code == 200
    first_body = first_response.json()
    assert first_body["total_gross"] == "120.00"
    assert first_body["total_net"] == "120.00"

    second_response = client.get("/v1/months/2026/2/summary?auto_generate=true")
    assert second_response.status_code == 200
    second_body = second_response.json()
    assert second_body["total_gross"] == "120.00"
    assert second_body["total_net"] == "120.00"
