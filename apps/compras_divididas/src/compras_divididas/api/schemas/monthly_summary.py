"""Schemas for monthly summary response."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from compras_divididas.domain.money import format_money


class ParticipantBalanceResponse(BaseModel):
    """Participant contribution and net balance for a month."""

    participant_id: UUID
    paid_total: str = Field(pattern=r"^-?[0-9]+\.[0-9]{2}$")
    share_due: str = Field(pattern=r"^-?[0-9]+\.[0-9]{2}$")
    net_balance: str = Field(pattern=r"^-?[0-9]+\.[0-9]{2}$")

    @classmethod
    def from_values(
        cls,
        *,
        participant_id: UUID,
        paid_total: Decimal,
        share_due: Decimal,
        net_balance: Decimal,
    ) -> ParticipantBalanceResponse:
        return cls(
            participant_id=participant_id,
            paid_total=format_money(paid_total),
            share_due=format_money(share_due),
            net_balance=format_money(net_balance),
        )


class TransferInstructionResponse(BaseModel):
    """Transfer projection between debtor and creditor participants."""

    amount: str = Field(pattern=r"^-?[0-9]+\.[0-9]{2}$")
    debtor_participant_id: UUID | None
    creditor_participant_id: UUID | None

    @classmethod
    def from_values(
        cls,
        *,
        amount: Decimal,
        debtor_participant_id: UUID | None,
        creditor_participant_id: UUID | None,
    ) -> TransferInstructionResponse:
        return cls(
            amount=format_money(amount),
            debtor_participant_id=debtor_participant_id,
            creditor_participant_id=creditor_participant_id,
        )


class MonthlySummaryResponse(BaseModel):
    """Consolidated monthly summary."""

    competence_month: str = Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")
    total_gross: str = Field(pattern=r"^-?[0-9]+\.[0-9]{2}$")
    total_refunds: str = Field(pattern=r"^-?[0-9]+\.[0-9]{2}$")
    total_net: str = Field(pattern=r"^-?[0-9]+\.[0-9]{2}$")
    participants: list[ParticipantBalanceResponse] = Field(min_length=2, max_length=2)
    transfer: TransferInstructionResponse

    @classmethod
    def from_values(
        cls,
        *,
        competence_month: str,
        total_gross: Decimal,
        total_refunds: Decimal,
        total_net: Decimal,
        participants: list[ParticipantBalanceResponse],
        transfer: TransferInstructionResponse,
    ) -> MonthlySummaryResponse:
        return cls(
            competence_month=competence_month,
            total_gross=format_money(total_gross),
            total_refunds=format_money(total_refunds),
            total_net=format_money(total_net),
            participants=participants,
            transfer=transfer,
        )
