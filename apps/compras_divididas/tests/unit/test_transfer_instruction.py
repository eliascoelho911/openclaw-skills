from __future__ import annotations

from decimal import Decimal

from compras_divididas.services.monthly_summary_service import (
    ParticipantBalance,
    build_transfer_instruction,
)


def test_build_transfer_instruction_returns_debtor_creditor_and_amount() -> None:
    participant_a = "ana"
    participant_b = "bia"

    instruction = build_transfer_instruction(
        [
            ParticipantBalance(
                participant_id=participant_a,
                paid_total=Decimal("80.00"),
                share_due=Decimal("60.00"),
                net_balance=Decimal("20.00"),
            ),
            ParticipantBalance(
                participant_id=participant_b,
                paid_total=Decimal("40.00"),
                share_due=Decimal("60.00"),
                net_balance=Decimal("-20.00"),
            ),
        ]
    )

    assert instruction.amount == Decimal("20.00")
    assert instruction.debtor_participant_id == participant_b
    assert instruction.creditor_participant_id == participant_a


def test_build_transfer_instruction_returns_zero_for_balanced_month() -> None:
    participant_a = "ana"
    participant_b = "bia"

    instruction = build_transfer_instruction(
        [
            ParticipantBalance(
                participant_id=participant_a,
                paid_total=Decimal("50.00"),
                share_due=Decimal("50.00"),
                net_balance=Decimal("0.00"),
            ),
            ParticipantBalance(
                participant_id=participant_b,
                paid_total=Decimal("50.00"),
                share_due=Decimal("50.00"),
                net_balance=Decimal("0.00"),
            ),
        ]
    )

    assert instruction.amount == Decimal("0.00")
    assert instruction.debtor_participant_id is None
    assert instruction.creditor_participant_id is None
