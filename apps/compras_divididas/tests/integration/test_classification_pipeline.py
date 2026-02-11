from compras_divididas.application.use_cases.close_month import (
    CloseMonthRequest,
    CloseMonthUseCase,
)


def test_classification_pipeline_with_mixed_batch() -> None:
    request = CloseMonthRequest.model_validate(
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
                },
                {
                    "message_id": "m2",
                    "author_external_id": "elias",
                    "author_display_name": "Elias",
                    "content": "Mercado R$20",
                    "sent_at": "2026-02-05T19:12:00-03:00",
                },
                {
                    "message_id": "m3",
                    "author_external_id": "esposa",
                    "author_display_name": "Esposa",
                    "content": "Farmacia sem valor",
                    "sent_at": "2026-02-06T12:35:00-03:00",
                },
                {
                    "message_id": "m4",
                    "author_external_id": "esposa",
                    "author_display_name": "Esposa",
                    "content": "bom dia amor",
                    "sent_at": "2026-02-06T12:40:00-03:00",
                },
                {
                    "message_id": "m5",
                    "author_external_id": "elias",
                    "author_display_name": "Elias",
                    "content": "Mercado -10",
                    "sent_at": "2026-02-07T11:00:00-03:00",
                },
                {
                    "message_id": "m6",
                    "author_external_id": "esposa",
                    "author_display_name": "Esposa",
                    "content": "extorno farmacia -5",
                    "sent_at": "2026-02-07T11:03:00-03:00",
                },
            ],
        }
    )

    report = CloseMonthUseCase().execute(request)

    assert report.counts.valid == 2
    assert report.counts.invalid == 2
    assert report.counts.ignored == 1
    assert report.counts.deduplicated == 1
    assert report.transfer_instruction.payer_external_id == "esposa"
    assert report.transfer_instruction.receiver_external_id == "elias"
    assert report.transfer_instruction.amount_cents == 2500

    rejected_by_message = {
        item["message_id"]: item["reason_code"] for item in report.rejected_entries
    }
    assert rejected_by_message["m3"] == "missing_amount"
    assert rejected_by_message["m4"] == "non_financial"
    assert rejected_by_message["m5"] == "negative_without_refund_keyword"
    assert report.deduplicated_entries[0]["message_id"] == "m2"
