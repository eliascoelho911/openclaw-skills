"""Global API exception handlers aligned with contract response shape."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from compras_divididas.domain.errors import (
    DomainError,
    DuplicateExternalIDError,
    compose_error_message,
)


def _error_payload(code: str, message: str, details: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if details:
        payload["details"] = details
    return payload


async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
    """Serialize domain error to contract-compliant response."""

    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(exc.code, exc.message, exc.details),
    )


async def handle_validation_error(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    """Map request validation failures to HTTP 400 contract."""

    return JSONResponse(
        status_code=HTTPStatus.BAD_REQUEST,
        content=_error_payload(
            code="INVALID_REQUEST",
            message=compose_error_message(
                cause="Request payload validation failed.",
                action="Fix the invalid fields and send the request again.",
            ),
            details={"errors": jsonable_encoder(exc.errors())},
        ),
    )


async def handle_integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
    """Translate persistence integrity errors to domain-compatible responses."""

    error_text = str(exc.orig)
    if "uq_financial_movements_competence_payer_external_id" in error_text:
        duplicate_error = DuplicateExternalIDError(
            message=compose_error_message(
                cause=(
                    "external_id is already used for this participant "
                    "in this competence month."
                ),
                action="Use a unique external_id or omit this field.",
            )
        )
        return JSONResponse(
            status_code=duplicate_error.status_code,
            content=_error_payload(
                duplicate_error.code,
                duplicate_error.message,
                duplicate_error.details,
            ),
        )

    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content=_error_payload(
            code="PERSISTENCE_ERROR",
            message=compose_error_message(
                cause="A persistence constraint was violated.",
                action="Review request data consistency and retry.",
            ),
            details={},
        ),
    )


async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    """Serialize unexpected failures with generic message."""

    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content=_error_payload(
            code="INTERNAL_SERVER_ERROR",
            message=compose_error_message(
                cause="An unexpected internal error occurred.",
                action="Retry later or contact support if the error persists.",
            ),
            details={"error_type": type(exc).__name__},
        ),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Attach all global handlers to the FastAPI application."""

    app.add_exception_handler(DomainError, cast(Any, handle_domain_error))
    app.add_exception_handler(
        RequestValidationError, cast(Any, handle_validation_error)
    )
    app.add_exception_handler(IntegrityError, cast(Any, handle_integrity_error))
    app.add_exception_handler(Exception, handle_unexpected_error)
