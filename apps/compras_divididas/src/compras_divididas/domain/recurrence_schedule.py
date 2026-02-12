"""Calendar helpers for monthly recurrence competence calculations."""

from __future__ import annotations

import calendar
from datetime import date


def is_first_day_of_month(value: date) -> bool:
    """Return whether a date is the first day of its month."""

    return value.day == 1


def normalize_competence_month(value: date) -> date:
    """Normalize any date to the first day of the same month."""

    return date(year=value.year, month=value.month, day=1)


def add_months(competence_month: date, months: int) -> date:
    """Return competence month shifted by a month offset."""

    normalized = normalize_competence_month(competence_month)
    absolute_month = ((normalized.year - 1) * 12 + normalized.month - 1) + months
    if absolute_month < 0:
        msg = "Resulting competence month is before year 0001."
        raise ValueError(msg)

    target_year = absolute_month // 12 + 1
    target_month = absolute_month % 12 + 1
    return date(year=target_year, month=target_month, day=1)


def scheduled_date_for_month(*, competence_month: date, reference_day: int) -> date:
    """Return scheduled occurrence date adjusted to valid day in month."""

    if reference_day < 1 or reference_day > 31:
        msg = "reference_day must be between 1 and 31."
        raise ValueError(msg)

    normalized = normalize_competence_month(competence_month)
    _, month_last_day = calendar.monthrange(normalized.year, normalized.month)
    day = min(reference_day, month_last_day)
    return date(year=normalized.year, month=normalized.month, day=day)
