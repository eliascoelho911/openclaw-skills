from compras_divididas.application.use_cases.close_month import (
    CloseMonthRequest,
    CloseMonthUseCase,
)


def test_close_month_happy_path() -> None:
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
                    "author_external_id": "esposa",
                    "author_display_name": "Esposa",
                    "content": "Farmacia R$35,50",
                    "sent_at": "2026-02-06T12:35:00-03:00",
                },
            ],
        }
    )

    report = CloseMonthUseCase().execute(request)

    assert report.transfer_instruction.payer_external_id == "elias"
    assert report.transfer_instruction.receiver_external_id == "esposa"
    assert report.transfer_instruction.amount_cents == 1550
    assert report.transfer_instruction.amount_brl == "R$ 15,50"
    assert report.counts.valid == 2
    assert report.counts.invalid == 0
    assert report.counts.ignored == 0
