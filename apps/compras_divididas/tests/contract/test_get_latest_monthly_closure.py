from datetime import datetime

from compras_divididas.api.monthly_closures import (
    create_monthly_closure,
    get_latest_monthly_closure,
)


def test_get_latest_monthly_closure_contract() -> None:
    create_status_1, first_payload = create_monthly_closure(
        {
            "period": {"year": 2026, "month": 4},
            "participants": [
                {"external_id": "elias", "display_name": "Elias"},
                {"external_id": "esposa", "display_name": "Esposa"},
            ],
            "messages": [
                {
                    "message_id": "l1",
                    "author_external_id": "elias",
                    "author_display_name": "Elias",
                    "content": "Mercado R$20",
                    "sent_at": "2026-04-05T19:10:00-03:00",
                }
            ],
        }
    )
    assert create_status_1 == 201

    create_status_2, second_payload = create_monthly_closure(
        {
            "period": {"year": 2026, "month": 4},
            "participants": [
                {"external_id": "elias", "display_name": "Elias"},
                {"external_id": "esposa", "display_name": "Esposa"},
            ],
            "messages": [
                {
                    "message_id": "l2",
                    "author_external_id": "esposa",
                    "author_display_name": "Esposa",
                    "content": "Farmacia R$35,50",
                    "sent_at": "2026-04-06T12:35:00-03:00",
                }
            ],
        }
    )
    assert create_status_2 == 201

    status_code, payload = get_latest_monthly_closure(2026, 4)

    assert status_code == 200
    expected_latest = max(
        [first_payload, second_payload],
        key=lambda item: (
            datetime.fromisoformat(item["created_at"]),
            item["closure_id"],
        ),
    )
    assert payload["closure_id"] == expected_latest["closure_id"]
    assert payload["period"] == {"year": 2026, "month": 4}
    assert "transfer_instruction" in payload


def test_get_latest_monthly_closure_returns_404_when_missing() -> None:
    status_code, payload = get_latest_monthly_closure(2030, 1)

    assert status_code == 404
    assert payload["error_code"] == "closure_not_found"
