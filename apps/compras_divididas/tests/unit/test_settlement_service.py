from compras_divididas.application.services.settlement_service import (
    calculate_settlement,
)


def test_settlement_when_participant_a_has_higher_total() -> None:
    decision = calculate_settlement(
        participant_a_external_id="elias",
        total_a_cents=3550,
        participant_b_external_id="esposa",
        total_b_cents=2000,
    )

    assert decision.payer_external_id == "esposa"
    assert decision.receiver_external_id == "elias"
    assert decision.transfer_amount_cents == 1550
    assert decision.net_balance_cents == 1550


def test_settlement_when_only_one_participant_has_entries() -> None:
    decision = calculate_settlement(
        participant_a_external_id="elias",
        total_a_cents=2500,
        participant_b_external_id="esposa",
        total_b_cents=0,
    )

    assert decision.payer_external_id == "esposa"
    assert decision.receiver_external_id == "elias"
    assert decision.transfer_amount_cents == 2500


def test_settlement_when_no_entries_exist() -> None:
    decision = calculate_settlement(
        participant_a_external_id="elias",
        total_a_cents=0,
        participant_b_external_id="esposa",
        total_b_cents=0,
    )

    assert decision.payer_external_id is None
    assert decision.receiver_external_id is None
    assert decision.transfer_amount_cents == 0
    assert decision.net_balance_cents == 0
