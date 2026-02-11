from compras_divididas.api.monthly_closures import create_monthly_closure


def test_create_monthly_closure_contract() -> None:
    status_code, payload = create_monthly_closure(
        {
            "period": {"year": 2026, "month": 2},
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
                    "sent_at": "2026-02-05T19:10:00-03:00",
                }
            ],
            "source": "manual_copy",
            "reprocess_mode": "new_version",
        }
    )

    assert status_code == 201
    assert isinstance(payload["closure_id"], str)
    assert isinstance(payload["run_id"], str)
    assert payload["status"] == "finalized"
    assert payload["period"] == {"year": 2026, "month": 2}

    assert len(payload["participants"]) == 2
    assert len(payload["totals_by_participant"]) == 2
    assert set(payload["counts"].keys()) == {
        "valid",
        "invalid",
        "ignored",
        "deduplicated",
    }

    transfer = payload["transfer_instruction"]
    assert set(transfer.keys()) == {
        "payer_external_id",
        "receiver_external_id",
        "amount_cents",
        "amount_brl",
        "message",
    }
