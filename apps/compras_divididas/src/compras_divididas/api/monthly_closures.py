"""Monthly closure API handlers."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from compras_divididas.application.use_cases.close_month import (
    CloseMonthRequest,
    CloseMonthUseCase,
    ParticipantCountError,
)


def create_monthly_closure(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Handle POST /v1/monthly-closures request payload."""
    try:
        request = CloseMonthRequest.model_validate(payload)
    except ValidationError as error:
        return 400, {
            "error_code": "invalid_request",
            "message": "Request payload is invalid",
            "details": [issue["msg"] for issue in error.errors()],
        }

    try:
        report = CloseMonthUseCase().execute(request)
    except ParticipantCountError as error:
        return 409, {
            "error_code": "participant_rule_violation",
            "message": str(error),
        }
    except ValueError as error:
        return 422, {
            "error_code": "validation_error",
            "message": str(error),
        }

    return 201, report.model_dump(mode="json")
