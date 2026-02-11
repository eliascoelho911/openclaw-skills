from uuid import uuid4

from compras_divididas.api.monthly_closures import (
    create_monthly_closure,
    get_monthly_closure_by_id,
)


def test_get_monthly_closure_by_id_contract() -> None:
    create_status, created_payload = create_monthly_closure(
        {
            "period": {"year": 2026, "month": 3},
            "participants": [
                {"external_id": "elias", "display_name": "Elias"},
                {"external_id": "esposa", "display_name": "Esposa"},
            ],
            "messages": [
                {
                    "message_id": "c1",
                    "author_external_id": "elias",
                    "author_display_name": "Elias",
                    "content": "Mercado R$20",
                    "sent_at": "2026-03-05T19:10:00-03:00",
                }
            ],
        }
    )
    assert create_status == 201

    status_code, payload = get_monthly_closure_by_id(created_payload["closure_id"])

    assert status_code == 200
    assert payload["closure_id"] == created_payload["closure_id"]
    assert payload["run_id"] == created_payload["run_id"]
    assert payload["period"] == {"year": 2026, "month": 3}
    assert isinstance(payload["valid_entries"], list)
    assert isinstance(payload["rejected_entries"], list)
    assert isinstance(payload["deduplicated_entries"], list)
    assert set(payload["counts"].keys()) == {
        "valid",
        "invalid",
        "ignored",
        "deduplicated",
    }


def test_get_monthly_closure_by_id_returns_404_when_missing() -> None:
    status_code, payload = get_monthly_closure_by_id(str(uuid4()))

    assert status_code == 404
    assert payload["error_code"] == "closure_not_found"
