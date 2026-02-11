from compras_divididas.api.monthly_closures import (
    create_monthly_closure,
    get_latest_monthly_closure,
    get_monthly_closure_by_id,
)


def test_detailed_report_with_rejected_and_deduplicated_entries() -> None:
    create_status, created_payload = create_monthly_closure(
        {
            "period": {"year": 2026, "month": 5},
            "participants": [
                {"external_id": "elias", "display_name": "Elias"},
                {"external_id": "esposa", "display_name": "Esposa"},
            ],
            "messages": [
                {
                    "message_id": "m1",
                    "author_external_id": "elias",
                    "author_display_name": "Elias",
                    "content": "Mercado R$20",
                    "sent_at": "2026-05-05T19:10:00-03:00",
                },
                {
                    "message_id": "m2",
                    "author_external_id": "elias",
                    "author_display_name": "Elias",
                    "content": "Mercado R$20",
                    "sent_at": "2026-05-05T19:12:00-03:00",
                },
                {
                    "message_id": "m3",
                    "author_external_id": "esposa",
                    "author_display_name": "Esposa",
                    "content": "Farmacia sem valor",
                    "sent_at": "2026-05-06T12:35:00-03:00",
                },
                {
                    "message_id": "m4",
                    "author_external_id": "esposa",
                    "author_display_name": "Esposa",
                    "content": "bom dia amor",
                    "sent_at": "2026-05-06T12:40:00-03:00",
                },
            ],
        }
    )
    assert create_status == 201

    by_id_status, by_id_payload = get_monthly_closure_by_id(
        created_payload["closure_id"]
    )
    assert by_id_status == 200

    assert by_id_payload["counts"] == {
        "valid": 1,
        "invalid": 1,
        "ignored": 1,
        "deduplicated": 1,
    }
    assert len(by_id_payload["valid_entries"]) == 1
    assert len(by_id_payload["rejected_entries"]) == 2
    assert len(by_id_payload["deduplicated_entries"]) == 1

    rejected_by_message = {
        item["message_id"]: item["reason_code"]
        for item in by_id_payload["rejected_entries"]
    }
    assert rejected_by_message == {
        "m3": "missing_amount",
        "m4": "non_financial",
    }

    deduplicated_entry = by_id_payload["deduplicated_entries"][0]
    assert deduplicated_entry["message_id"] == "m2"
    assert deduplicated_entry["duplicated_of_entry_id"]

    latest_status, latest_payload = get_latest_monthly_closure(2026, 5)
    assert latest_status == 200
    assert latest_payload["closure_id"] == created_payload["closure_id"]
    assert latest_payload["counts"] == by_id_payload["counts"]
