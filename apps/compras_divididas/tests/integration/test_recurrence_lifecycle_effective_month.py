"""Integration tests for recurrence lifecycle future-only effects."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from compras_divididas.db.models.financial_movement import FinancialMovement


def test_recurrence_edit_only_affects_future_competence(
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
    recurrence_id = create_response.json()["id"]

    feb_generation = client.post("/v1/months/2026/2/recurrences/generate")
    assert feb_generation.status_code == 200
    assert feb_generation.json()["generated_count"] == 1

    update_response = client.patch(
        f"/v1/recurrences/{recurrence_id}",
        json={
            "requested_by_participant_id": participant_a,
            "description": "Internet fibra",
            "amount": "139.90",
        },
    )
    assert update_response.status_code == 200

    mar_generation = client.post("/v1/months/2026/3/recurrences/generate")
    assert mar_generation.status_code == 200
    assert mar_generation.json()["generated_count"] == 1

    with sqlite_session_factory() as session:
        movements = list(
            session.scalars(
                select(FinancialMovement)
                .where(
                    FinancialMovement.external_id.like(f"recurrence:{recurrence_id}:%")
                )
                .order_by(FinancialMovement.competence_month.asc())
            )
        )

    assert len(movements) == 2
    assert movements[0].competence_month == date(2026, 2, 1)
    assert movements[0].amount == Decimal("120.00")
    assert movements[0].description == "Internet"
    assert movements[1].competence_month == date(2026, 3, 1)
    assert movements[1].amount == Decimal("139.90")
    assert movements[1].description == "Internet fibra"
