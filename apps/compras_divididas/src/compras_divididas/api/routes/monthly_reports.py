"""Monthly report and summary routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from compras_divididas.api.dependencies import get_monthly_summary_service
from compras_divididas.api.schemas.monthly_summary import (
    MonthlySummaryResponse,
    ParticipantBalanceResponse,
    TransferInstructionResponse,
)
from compras_divididas.services.monthly_summary_service import MonthlySummaryService

router = APIRouter(prefix="/months", tags=["Monthly Reports"])


@router.get("/{year}/{month}/summary", response_model=MonthlySummaryResponse)
def get_monthly_summary(
    year: Annotated[int, Path(ge=2000, le=2100)],
    month: Annotated[int, Path(ge=1, le=12)],
    service: Annotated[MonthlySummaryService, Depends(get_monthly_summary_service)],
) -> MonthlySummaryResponse:
    """Return consolidated monthly partial summary."""

    summary = service.get_summary(year=year, month=month)
    participant_rows = [
        ParticipantBalanceResponse.from_values(
            participant_id=item.participant_id,
            paid_total=item.paid_total,
            share_due=item.share_due,
            net_balance=item.net_balance,
        )
        for item in summary.participants
    ]

    return MonthlySummaryResponse.from_values(
        competence_month=f"{summary.competence_month.year:04d}-{summary.competence_month.month:02d}",
        total_gross=summary.total_gross,
        total_refunds=summary.total_refunds,
        total_net=summary.total_net,
        participants=participant_rows,
        transfer=TransferInstructionResponse.from_values(
            amount=summary.transfer.amount,
            debtor_participant_id=summary.transfer.debtor_participant_id,
            creditor_participant_id=summary.transfer.creditor_participant_id,
        ),
    )
