from __future__ import annotations

from fastapi.testclient import TestClient

from compras_divididas.api.app import create_app


def test_get_monthly_report_returns_200_with_contract_shape(
    client: TestClient, participants: tuple[str, str]
) -> None:
    participant_a, _ = participants
    assert (
        client.post(
            "/v1/movements",
            json={
                "type": "purchase",
                "amount": "100.00",
                "description": "Mercado",
                "occurred_at": "2026-02-10T12:00:00Z",
                "requested_by_participant_id": participant_a,
            },
        ).status_code
        == 201
    )

    response = client.get("/v1/months/2026/2/report")
    assert response.status_code == 200

    body = response.json()
    assert body["competence_month"] == "2026-02"
    assert body["total_gross"] == "100.00"
    assert body["total_refunds"] == "0.00"
    assert body["total_net"] == "100.00"
    assert len(body["participants"]) == 2
    assert set(body["transfer"].keys()) == {
        "amount",
        "debtor_participant_id",
        "creditor_participant_id",
    }


def test_get_monthly_report_returns_400_for_invalid_path_params(
    client: TestClient,
) -> None:
    response = client.get("/v1/months/2026/13/report")

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"


def test_openapi_contains_monthly_report_path() -> None:
    app = create_app()
    schema = app.openapi()
    get_operation = schema["paths"]["/v1/months/{year}/{month}/report"]["get"]
    response_codes = set(get_operation["responses"].keys())

    assert "200" in response_codes


def test_get_monthly_report_supports_auto_generate(
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

    response = client.get("/v1/months/2026/2/report?auto_generate=true")
    assert response.status_code == 200

    body = response.json()
    assert body["total_gross"] == "120.00"
    assert body["total_net"] == "120.00"
