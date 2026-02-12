"""Business service for monthly report generation."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from compras_divididas.services.monthly_summary_service import (
    MonthlySummaryProjection,
    MonthlySummaryService,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MonthlyReportService:
    """Generates monthly report reusing monthly summary aggregation."""

    monthly_summary_service: MonthlySummaryService

    def get_report(
        self,
        *,
        year: int,
        month: int,
        request_id: str | None,
        auto_generate: bool = False,
    ) -> MonthlySummaryProjection:
        projection = self.monthly_summary_service.get_summary(
            year=year,
            month=month,
            auto_generate=auto_generate,
        )
        competence_month = (
            f"{projection.competence_month.year:04d}-"
            f"{projection.competence_month.month:02d}"
        )

        for participant in projection.participants:
            logger.info(
                "monthly_report_generated",
                extra={
                    "participant_id": str(participant.participant_id),
                    "competence_month": competence_month,
                    "request_id": request_id,
                },
            )

        return projection
