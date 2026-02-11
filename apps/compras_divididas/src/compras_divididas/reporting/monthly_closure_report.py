"""Detailed report assembly helpers for monthly closures."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from compras_divididas.application.use_cases.close_month import MonthlyClosureReport

SortKey = tuple[datetime, str] | str


def _parse_entry_date(item: dict[str, Any]) -> datetime:
    raw_date = item.get("date")
    if isinstance(raw_date, str):
        try:
            return datetime.fromisoformat(raw_date)
        except ValueError:
            return datetime.min
    return datetime.min


class MonthlyClosureReportBuilder:
    """Build deterministic and auditable detailed monthly closure reports."""

    def build(self, report: MonthlyClosureReport) -> MonthlyClosureReport:
        """Return a normalized report with stable audit-friendly ordering."""
        valid_entries = self._sort_entries(
            report.valid_entries,
            key=lambda item: (_parse_entry_date(item), str(item.get("message_id", ""))),
        )
        rejected_entries = self._sort_entries(
            report.rejected_entries,
            key=lambda item: str(item.get("message_id", "")),
        )
        deduplicated_entries = self._sort_entries(
            report.deduplicated_entries,
            key=lambda item: str(item.get("message_id", "")),
        )
        return report.model_copy(
            update={
                "valid_entries": valid_entries,
                "rejected_entries": rejected_entries,
                "deduplicated_entries": deduplicated_entries,
            }
        )

    def _sort_entries(
        self,
        entries: list[dict[str, object]],
        *,
        key: Callable[[dict[str, Any]], SortKey],
    ) -> list[dict[str, object]]:
        sorted_entries = sorted(
            (dict(entry) for entry in entries),
            key=lambda item: key(item),
        )
        return [dict(item) for item in sorted_entries]
