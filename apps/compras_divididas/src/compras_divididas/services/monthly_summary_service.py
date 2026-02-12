"""Business service for monthly partial summary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from compras_divididas.db.models.participant import Participant
from compras_divididas.domain.money import quantize_money


class ParticipantRepositoryProtocol(Protocol):
    """Participant repository contract used by summary service."""

    def list_active_exactly_two(self) -> list[Participant]: ...


class MovementQueryRepositoryProtocol(Protocol):
    """Read repository contract used by summary service."""

    def get_monthly_totals(
        self, competence_month: date
    ) -> tuple[Decimal, Decimal, Decimal]: ...

    def get_paid_totals_by_participant(
        self, competence_month: date
    ) -> dict[str, Decimal]: ...


@dataclass(frozen=True, slots=True)
class ParticipantBalance:
    """Computed balance line for one participant."""

    participant_id: str
    paid_total: Decimal
    share_due: Decimal
    net_balance: Decimal


@dataclass(frozen=True, slots=True)
class TransferInstruction:
    """Projected transfer instruction for current monthly state."""

    amount: Decimal
    debtor_participant_id: str | None
    creditor_participant_id: str | None


@dataclass(frozen=True, slots=True)
class MonthlySummaryProjection:
    """Consolidated monthly values used by API response schema."""

    competence_month: date
    total_gross: Decimal
    total_refunds: Decimal
    total_net: Decimal
    participants: list[ParticipantBalance]
    transfer: TransferInstruction


def build_transfer_instruction(
    participant_balances: list[ParticipantBalance],
) -> TransferInstruction:
    """Build transfer instruction from participant net balances."""

    debtor = next(
        (
            participant
            for participant in participant_balances
            if participant.net_balance < 0
        ),
        None,
    )
    creditor = next(
        (
            participant
            for participant in participant_balances
            if participant.net_balance > 0
        ),
        None,
    )

    if debtor is None or creditor is None:
        return TransferInstruction(
            amount=Decimal("0.00"),
            debtor_participant_id=None,
            creditor_participant_id=None,
        )

    return TransferInstruction(
        amount=quantize_money(abs(debtor.net_balance)),
        debtor_participant_id=debtor.participant_id,
        creditor_participant_id=creditor.participant_id,
    )


class MonthlySummaryService:
    """Computes monthly partial summary and 50/50 balance split."""

    def __init__(
        self,
        *,
        participant_repository: ParticipantRepositoryProtocol,
        movement_query_repository: MovementQueryRepositoryProtocol,
    ) -> None:
        self._participant_repository = participant_repository
        self._movement_query_repository = movement_query_repository

    def get_summary(self, *, year: int, month: int) -> MonthlySummaryProjection:
        competence_month = date(year=year, month=month, day=1)
        participants = self._participant_repository.list_active_exactly_two()
        gross, refunds, net = self._movement_query_repository.get_monthly_totals(
            competence_month
        )
        paid_totals = self._movement_query_repository.get_paid_totals_by_participant(
            competence_month
        )

        share_due = quantize_money(net / Decimal("2"))
        participant_balances: list[ParticipantBalance] = []
        for participant in participants:
            participant_id = str(participant.id)
            paid_total = paid_totals.get(participant_id, Decimal("0.00"))
            net_balance = quantize_money(paid_total - share_due)
            participant_balances.append(
                ParticipantBalance(
                    participant_id=participant_id,
                    paid_total=paid_total,
                    share_due=share_due,
                    net_balance=net_balance,
                )
            )

        transfer = build_transfer_instruction(participant_balances)
        return MonthlySummaryProjection(
            competence_month=competence_month,
            total_gross=gross,
            total_refunds=refunds,
            total_net=net,
            participants=participant_balances,
            transfer=transfer,
        )
