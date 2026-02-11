"""Monthly report and summary routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request

from compras_divididas.api.dependencies import (
    get_monthly_report_service,
    get_monthly_summary_service,
)
from compras_divididas.api.schemas.monthly_summary import MonthlySummaryResponse
from compras_divididas.services.monthly_report_service import MonthlyReportService
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
    return MonthlySummaryResponse.from_projection(summary)


@router.get("/{year}/{month}/report", response_model=MonthlySummaryResponse)
def get_monthly_report(
    year: Annotated[int, Path(ge=2000, le=2100)],
    month: Annotated[int, Path(ge=1, le=12)],
    request: Request,
    service: Annotated[MonthlyReportService, Depends(get_monthly_report_service)],
) -> MonthlySummaryResponse:
    """Return consolidated monthly report generated on demand."""

    summary = service.get_report(
        year=year,
        month=month,
        request_id=request.headers.get("x-request-id"),
    )
    return MonthlySummaryResponse.from_projection(summary)
