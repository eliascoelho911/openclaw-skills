"""Domain exceptions used across API and services."""

from __future__ import annotations

from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any


def compose_error_message(*, cause: str, action: str) -> str:
    """Build a user-facing error message with cause and corrective action."""

    return f"Cause: {cause} Action: {action}"


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

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="INVALID_REQUEST",
            message=message
            or compose_error_message(
                cause="Request data violates business rules.",
                action="Adjust the input fields and try again.",
            ),
            status_code=HTTPStatus.BAD_REQUEST,
            details=details or {},
        )


class PurchaseNotFoundError(DomainError):
    """Raised when refund target purchase cannot be resolved."""

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="PURCHASE_NOT_FOUND",
            message=message
            or compose_error_message(
                cause="Original purchase cannot be resolved for this refund.",
                action=(
                    "Provide a valid original_purchase_id or "
                    "original_purchase_external_id."
                ),
            ),
            status_code=HTTPStatus.NOT_FOUND,
            details=details or {},
        )


class DuplicateExternalIDError(DomainError):
    """Raised when movement deduplication rejects duplicated external_id."""

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="DUPLICATE_EXTERNAL_ID",
            message=message
            or compose_error_message(
                cause=(
                    "external_id is already used for this participant in "
                    "the competence month."
                ),
                action=(
                    "Use a unique external_id or omit external_id for this movement."
                ),
            ),
            status_code=HTTPStatus.CONFLICT,
            details=details or {},
        )


class RefundLimitExceededError(DomainError):
    """Raised when cumulative refunds exceed original purchase amount."""

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="REFUND_LIMIT_EXCEEDED",
            message=message
            or compose_error_message(
                cause="Refund total would exceed the original purchase amount.",
                action="Reduce the refund amount or reference the correct purchase.",
            ),
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details=details or {},
        )


class DomainInvariantError(DomainError):
    """Raised when fixed domain assumptions are violated."""

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="DOMAIN_INVARIANT_VIOLATION",
            message=message
            or compose_error_message(
                cause="A required domain invariant is not satisfied.",
                action="Verify base data setup and retry the operation.",
            ),
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details=details or {},
        )


class RecurrenceNotFoundError(DomainError):
    """Raised when recurrence rule cannot be resolved."""

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="RECURRENCE_NOT_FOUND",
            message=message
            or compose_error_message(
                cause="Recurrence rule was not found.",
                action="Use a valid recurrence_id and retry.",
            ),
            status_code=HTTPStatus.NOT_FOUND,
            details=details or {},
        )


class InvalidRecurrenceStateTransitionError(DomainError):
    """Raised when recurrence lifecycle transition is not allowed."""

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="INVALID_RECURRENCE_STATE_TRANSITION",
            message=message
            or compose_error_message(
                cause="Recurrence status transition is not allowed.",
                action="Apply a valid transition for the current status.",
            ),
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details=details or {},
        )


class StartCompetenceLockedError(DomainError):
    """Raised when start competence month change is blocked."""

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="START_COMPETENCE_LOCKED",
            message=message
            or compose_error_message(
                cause="start_competence_month cannot change after first generation.",
                action="Keep current start_competence_month and edit other fields.",
            ),
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details=details or {},
        )


class DuplicateRecurrenceOccurrenceError(DomainError):
    """Raised when recurrence occurrence idempotency constraint is hit."""

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="DUPLICATE_RECURRENCE_OCCURRENCE",
            message=message
            or compose_error_message(
                cause=(
                    "An occurrence already exists for this recurrence and competence."
                ),
                action=(
                    "Treat this operation as idempotent or use another "
                    "competence month."
                ),
            ),
            status_code=HTTPStatus.CONFLICT,
            details=details or {},
        )


class RecurrenceMovementAlreadyLinkedError(DomainError):
    """Raised when one movement is linked to multiple occurrences."""

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="RECURRENCE_MOVEMENT_ALREADY_LINKED",
            message=message
            or compose_error_message(
                cause="Movement is already linked to another recurrence occurrence.",
                action=(
                    "Use the existing linked occurrence instead of creating a new link."
                ),
            ),
            status_code=HTTPStatus.CONFLICT,
            details=details or {},
        )
