"""Monthly closure API handlers."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError

from compras_divididas.application.use_cases.close_month import (
    CloseMonthRequest,
    CloseMonthUseCase,
    ParticipantCountError,
)
from compras_divididas.application.use_cases.get_monthly_closure import (
    GetLatestMonthlyClosureUseCase,
    GetMonthlyClosureByIdUseCase,
    InMemoryMonthlyClosureReportRepository,
    MonthlyClosureNotFoundError,
)


class LatestMonthlyClosurePath(BaseModel):
    """Path parameters for latest closure period queries."""

    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


_CLOSURE_REPORT_REPOSITORY = InMemoryMonthlyClosureReportRepository()


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
        report = CloseMonthUseCase(closure_writer=_CLOSURE_REPORT_REPOSITORY).execute(
            request
        )
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


def get_monthly_closure_by_id(closure_id: str) -> tuple[int, dict[str, Any]]:
    """Handle GET /v1/monthly-closures/{closure_id}."""
    try:
        parsed_closure_id = UUID(closure_id)
    except ValueError:
        return 404, {
            "error_code": "closure_not_found",
            "message": "Monthly closure not found",
        }

    try:
        report = GetMonthlyClosureByIdUseCase(_CLOSURE_REPORT_REPOSITORY).execute(
            parsed_closure_id
        )
    except MonthlyClosureNotFoundError as error:
        return 404, {
            "error_code": "closure_not_found",
            "message": str(error),
        }

    return 200, report.model_dump(mode="json")


def get_latest_monthly_closure(year: int, month: int) -> tuple[int, dict[str, Any]]:
    """Handle GET /v1/monthly-closures/{year}/{month}/latest."""
    try:
        path_params = LatestMonthlyClosurePath(year=year, month=month)
    except ValidationError as error:
        return 400, {
            "error_code": "invalid_request",
            "message": "Path parameters are invalid",
            "details": [issue["msg"] for issue in error.errors()],
        }

    try:
        report = GetLatestMonthlyClosureUseCase(_CLOSURE_REPORT_REPOSITORY).execute(
            path_params.year,
            path_params.month,
        )
    except MonthlyClosureNotFoundError as error:
        return 404, {
            "error_code": "closure_not_found",
            "message": str(error),
        }

    return 200, report.model_dump(mode="json")
