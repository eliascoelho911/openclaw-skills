"""Bilateral settlement calculation service."""

from __future__ import annotations

from dataclasses import dataclass

from compras_divididas.domain.value_objects import MoneyBRL


@dataclass(frozen=True, slots=True)
class SettlementDecision:
    """Represents the final transfer instruction for the month."""

    net_balance_cents: int
    payer_external_id: str | None
    receiver_external_id: str | None
    transfer_amount_cents: int
    message: str


def calculate_settlement(
    participant_a_external_id: str,
    total_a_cents: int,
    participant_b_external_id: str,
    total_b_cents: int,
) -> SettlementDecision:
    """Compute bilateral transfer from participant totals."""
    net_balance_cents = total_a_cents - total_b_cents
    if net_balance_cents == 0:
        return SettlementDecision(
            net_balance_cents=0,
            payer_external_id=None,
            receiver_external_id=None,
            transfer_amount_cents=0,
            message="Nao ha repasse pendente.",
        )

    if net_balance_cents > 0:
        transfer_amount_cents = net_balance_cents
        payer_external_id = participant_b_external_id
        receiver_external_id = participant_a_external_id
    else:
        transfer_amount_cents = abs(net_balance_cents)
        payer_external_id = participant_a_external_id
        receiver_external_id = participant_b_external_id

    transfer_brl = MoneyBRL(cents=transfer_amount_cents).to_brl()
    message = (
        f"{payer_external_id} deve pagar {transfer_brl} para {receiver_external_id}."
    )
    return SettlementDecision(
        net_balance_cents=net_balance_cents,
        payer_external_id=payer_external_id,
        receiver_external_id=receiver_external_id,
        transfer_amount_cents=transfer_amount_cents,
        message=message,
    )
