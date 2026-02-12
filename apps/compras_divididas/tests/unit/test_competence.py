from datetime import datetime
from zoneinfo import ZoneInfo

from compras_divididas.domain.competence import (
    APP_TIMEZONE,
    competence_month,
    competence_month_label,
    resolve_occurred_at,
)


def test_resolve_occurred_at_converts_aware_value_to_sao_paulo() -> None:
    value = datetime(2026, 2, 1, 15, 0, tzinfo=ZoneInfo("UTC"))

    resolved = resolve_occurred_at(value)

    assert resolved.tzinfo == APP_TIMEZONE
    assert resolved.hour == 12


def test_resolve_occurred_at_defaults_to_now_with_timezone() -> None:
    resolved = resolve_occurred_at(None)

    assert resolved.tzinfo == APP_TIMEZONE


def test_competence_month_and_label() -> None:
    value = datetime(2026, 2, 20, 10, 0, tzinfo=APP_TIMEZONE)

    assert competence_month(value).isoformat() == "2026-02-01"
    assert competence_month_label(value) == "2026-02"
