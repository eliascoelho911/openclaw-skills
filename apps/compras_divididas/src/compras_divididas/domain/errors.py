"""Domain exceptions used across API and services."""

from __future__ import annotations

from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any


@dataclass(slots=True)
class DomainError(Exception):
    """Base exception for predictable domain failures."""

    code: str
    message: str
    status_code: int
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


class InvalidRequestError(DomainError):
    """Raised when user sends semantically invalid input."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="INVALID_REQUEST",
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
            details=details or {},
        )


class PurchaseNotFoundError(DomainError):
    """Raised when refund target purchase cannot be resolved."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="PURCHASE_NOT_FOUND",
            message=message,
            status_code=HTTPStatus.NOT_FOUND,
            details=details or {},
        )


class DuplicateExternalIDError(DomainError):
    """Raised when movement deduplication rejects duplicated external_id."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="DUPLICATE_EXTERNAL_ID",
            message=message,
            status_code=HTTPStatus.CONFLICT,
            details=details or {},
        )


class RefundLimitExceededError(DomainError):
    """Raised when cumulative refunds exceed original purchase amount."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="REFUND_LIMIT_EXCEEDED",
            message=message,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details=details or {},
        )


class DomainInvariantError(DomainError):
    """Raised when fixed domain assumptions are violated."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="DOMAIN_INVARIANT_VIOLATION",
            message=message,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details=details or {},
        )
