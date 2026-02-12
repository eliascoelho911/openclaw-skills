"""Unit tests for recurrence schedule helpers."""

from __future__ import annotations

from datetime import date

from compras_divididas.domain.recurrence_schedule import (
    can_transition_occurrence_status,
    scheduled_date_for_month,
)


def test_scheduled_date_adjusts_to_february_last_day_non_leap_year() -> None:
    scheduled = scheduled_date_for_month(
        competence_month=date(2026, 2, 1),
        reference_day=31,
    )

    assert scheduled == date(2026, 2, 28)


def test_scheduled_date_adjusts_to_february_last_day_leap_year() -> None:
    scheduled = scheduled_date_for_month(
        competence_month=date(2024, 2, 1),
        reference_day=31,
    )

    assert scheduled == date(2024, 2, 29)


def test_occurrence_transition_matrix_allows_only_supported_transitions() -> None:
    assert can_transition_occurrence_status(current="pending", target="generated")
    assert can_transition_occurrence_status(current="pending", target="blocked")
    assert can_transition_occurrence_status(current="pending", target="failed")
    assert can_transition_occurrence_status(current="failed", target="pending")

    assert not can_transition_occurrence_status(current="generated", target="pending")
    assert not can_transition_occurrence_status(current="blocked", target="pending")
