"""Monthly competence helpers based on fixed Sao Paulo timezone."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

APP_TIMEZONE = ZoneInfo("America/Sao_Paulo")


def resolve_occurred_at(occurred_at: datetime | None) -> datetime:
    """Return occurred_at value or current Sao Paulo timestamp when absent."""

    if occurred_at is None:
        return datetime.now(tz=APP_TIMEZONE)
    if occurred_at.tzinfo is None:
        return occurred_at.replace(tzinfo=APP_TIMEZONE)
    return occurred_at.astimezone(APP_TIMEZONE)


def competence_month(occurred_at: datetime) -> date:
    """Compute first day of month in Sao Paulo timezone for given timestamp."""

    localized = occurred_at.astimezone(APP_TIMEZONE)
    return date(year=localized.year, month=localized.month, day=1)


def competence_month_label(occurred_at: datetime) -> str:
    """Return competence month label as YYYY-MM."""

    month_value = competence_month(occurred_at)
    return f"{month_value.year:04d}-{month_value.month:02d}"
