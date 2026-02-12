"""Schemas for monthly summary response."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from compras_divididas.api.schemas.participants import ParticipantId
from compras_divididas.domain.money import format_money

if TYPE_CHECKING:
    from compras_divididas.services.monthly_summary_service import (
        MonthlySummaryProjection,
    )


class ParticipantBalanceResponse(BaseModel):
    """Participant contribution and net balance for a month."""

    participant_id: ParticipantId
    paid_total: str = Field(pattern=r"^-?[0-9]+\.[0-9]{2}$")
    share_due: str = Field(pattern=r"^-?[0-9]+\.[0-9]{2}$")
    net_balance: str = Field(pattern=r"^-?[0-9]+\.[0-9]{2}$")

    @classmethod
    def from_values(
        cls,
        *,
        participant_id: ParticipantId,
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
    debtor_participant_id: ParticipantId | None
    creditor_participant_id: ParticipantId | None

    @classmethod
    def from_values(
        cls,
        *,
        amount: Decimal,
        debtor_participant_id: ParticipantId | None,
        creditor_participant_id: ParticipantId | None,
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

    @classmethod
    def from_projection(
        cls, projection: MonthlySummaryProjection
    ) -> MonthlySummaryResponse:
        participant_rows = [
            ParticipantBalanceResponse.from_values(
                participant_id=item.participant_id,
                paid_total=item.paid_total,
                share_due=item.share_due,
                net_balance=item.net_balance,
            )
            for item in projection.participants
        ]
        return cls.from_values(
            competence_month=f"{projection.competence_month.year:04d}-{projection.competence_month.month:02d}",
            total_gross=projection.total_gross,
            total_refunds=projection.total_refunds,
            total_net=projection.total_net,
            participants=participant_rows,
            transfer=TransferInstructionResponse.from_values(
                amount=projection.transfer.amount,
                debtor_participant_id=projection.transfer.debtor_participant_id,
                creditor_participant_id=projection.transfer.creditor_participant_id,
            ),
        )
