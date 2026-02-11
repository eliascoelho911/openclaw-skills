"""Use cases to query monthly closure reports."""

from __future__ import annotations

from collections import defaultdict
from typing import Protocol
from uuid import UUID

from compras_divididas.application.use_cases.close_month import MonthlyClosureReport
from compras_divididas.reporting.monthly_closure_report import (
    MonthlyClosureReportBuilder,
)


class MonthlyClosureNotFoundError(LookupError):
    """Raised when a closure cannot be found for the query."""


class MonthlyClosureReportRepository(Protocol):
    """Port to store and query monthly closure reports."""

    def save(self, report: MonthlyClosureReport) -> None:
        """Persist one monthly closure report."""

    def get_by_id(self, closure_id: UUID) -> MonthlyClosureReport | None:
        """Return closure report by id when available."""

    def get_latest_by_period(
        self, year: int, month: int
    ) -> MonthlyClosureReport | None:
        """Return the latest closure report for a period."""


class InMemoryMonthlyClosureReportRepository:
    """In-memory repository used by API handlers and tests."""

    def __init__(self) -> None:
        self._reports_by_id: dict[UUID, MonthlyClosureReport] = {}
        self._report_ids_by_period: dict[tuple[int, int], list[UUID]] = defaultdict(
            list
        )

    def save(self, report: MonthlyClosureReport) -> None:
        self._reports_by_id[report.closure_id] = report
        period_key = (report.period.year, report.period.month)
        self._report_ids_by_period[period_key].append(report.closure_id)

    def get_by_id(self, closure_id: UUID) -> MonthlyClosureReport | None:
        return self._reports_by_id.get(closure_id)

    def get_latest_by_period(
        self, year: int, month: int
    ) -> MonthlyClosureReport | None:
        period_key = (year, month)
        report_ids = self._report_ids_by_period.get(period_key)
        if not report_ids:
            return None

        candidates = [self._reports_by_id[report_id] for report_id in report_ids]
        return max(
            candidates,
            key=lambda report: (report.created_at, str(report.closure_id)),
        )


class GetMonthlyClosureByIdUseCase:
    """Return one closure report by identifier."""

    def __init__(
        self,
        repository: MonthlyClosureReportRepository,
        report_builder: MonthlyClosureReportBuilder | None = None,
    ) -> None:
        self._repository = repository
        self._report_builder = report_builder or MonthlyClosureReportBuilder()

    def execute(self, closure_id: UUID) -> MonthlyClosureReport:
        report = self._repository.get_by_id(closure_id)
        if report is None:
            raise MonthlyClosureNotFoundError("Monthly closure not found")
        return self._report_builder.build(report)


class GetLatestMonthlyClosureUseCase:
    """Return the latest closure report for a period."""

    def __init__(
        self,
        repository: MonthlyClosureReportRepository,
        report_builder: MonthlyClosureReportBuilder | None = None,
    ) -> None:
        self._repository = repository
        self._report_builder = report_builder or MonthlyClosureReportBuilder()

    def execute(self, year: int, month: int) -> MonthlyClosureReport:
        report = self._repository.get_latest_by_period(year, month)
        if report is None:
            raise MonthlyClosureNotFoundError("Monthly closure not found")
        return self._report_builder.build(report)
