"""Recurrence API schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from compras_divididas.api.schemas.participants import ParticipantId
from compras_divididas.db.models.recurrence_rule import RecurrenceRule
from compras_divididas.domain.money import format_money
from compras_divididas.services.recurrence_generation_service import (
    BlockedRecurrenceItem,
    GenerateRecurrencesResult,
)

RecurrencePeriodicity = Literal["monthly"]
RecurrenceStatus = Literal["active", "paused", "ended"]


def parse_competence_month(value: str) -> date:
    """Parse YYYY-MM string into first day date."""

    year_text, month_text = value.split("-", maxsplit=1)
    return date(year=int(year_text), month=int(month_text), day=1)


def format_competence_month(value: date) -> str:
    """Format first-day month date as YYYY-MM."""

    return f"{value.year:04d}-{value.month:02d}"


class CreateRecurrenceRequest(BaseModel):
    """Payload for recurrence creation."""

    description: str = Field(min_length=1, max_length=280)
    amount: str = Field(pattern=r"^[0-9]+\.[0-9]{2}$")
    payer_participant_id: ParticipantId
    requested_by_participant_id: ParticipantId
    split_config: dict[str, Any]
    reference_day: int = Field(ge=1, le=31)
    start_competence_month: str = Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")
    end_competence_month: str | None = Field(
        default=None,
        pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$",
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Description cannot be blank.")
        return trimmed

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: str) -> str:
        try:
            amount_decimal = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Amount must be a decimal number.") from exc
        if amount_decimal <= Decimal("0"):
            raise ValueError("Amount must be greater than zero.")
        return value

    @model_validator(mode="after")
    def validate_month_range(self) -> CreateRecurrenceRequest:
        if self.end_competence_month is None:
            return self

        start_month = parse_competence_month(self.start_competence_month)
        end_month = parse_competence_month(self.end_competence_month)
        if end_month < start_month:
            raise ValueError(
                "end_competence_month cannot be earlier than start_competence_month."
            )
        return self


class RecurrenceResponse(BaseModel):
    """Serialized recurrence returned by API."""

    id: UUID
    description: str
    amount: str = Field(pattern=r"^-?[0-9]+\.[0-9]{2}$")
    payer_participant_id: ParticipantId
    requested_by_participant_id: ParticipantId
    split_config: dict[str, Any]
    periodicity: RecurrencePeriodicity
    reference_day: int = Field(ge=1, le=31)
    start_competence_month: str = Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")
    end_competence_month: str | None = Field(
        default=None,
        pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$",
    )
    status: RecurrenceStatus
    first_generated_competence_month: str | None = Field(
        default=None,
        pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$",
    )
    last_processed_competence_month: str | None = Field(
        default=None,
        pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$",
    )
    next_competence_month: str = Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, recurrence: RecurrenceRule) -> RecurrenceResponse:
        return cls(
            id=recurrence.id,
            description=recurrence.description,
            amount=format_money(recurrence.amount),
            payer_participant_id=str(recurrence.payer_participant_id),
            requested_by_participant_id=str(recurrence.requested_by_participant_id),
            split_config=recurrence.split_config,
            periodicity=recurrence.periodicity.value,
            reference_day=recurrence.reference_day,
            start_competence_month=format_competence_month(
                recurrence.start_competence_month
            ),
            end_competence_month=format_competence_month(
                recurrence.end_competence_month
            )
            if recurrence.end_competence_month
            else None,
            status=recurrence.status.value,
            first_generated_competence_month=format_competence_month(
                recurrence.first_generated_competence_month
            )
            if recurrence.first_generated_competence_month
            else None,
            last_processed_competence_month=format_competence_month(
                recurrence.last_generated_competence_month
            )
            if recurrence.last_generated_competence_month
            else None,
            next_competence_month=format_competence_month(
                recurrence.next_competence_month
            ),
            created_at=recurrence.created_at,
            updated_at=recurrence.updated_at,
        )


class RecurrenceListResponse(BaseModel):
    """Paginated recurrence list response."""

    items: list[RecurrenceResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)

    @classmethod
    def from_models(
        cls,
        *,
        items: list[RecurrenceRule],
        total: int,
        limit: int,
        offset: int,
    ) -> RecurrenceListResponse:
        return cls(
            items=[RecurrenceResponse.from_model(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )


class GenerateRecurrencesRequest(BaseModel):
    """Payload for monthly recurrence generation."""

    requested_by_participant_id: ParticipantId | None = None
    dry_run: bool = False
    include_blocked_details: bool = True


class UpdateRecurrenceRequest(BaseModel):
    """Payload for recurrence updates."""

    requested_by_participant_id: ParticipantId
    description: str | None = Field(default=None, min_length=1, max_length=280)
    amount: str | None = Field(default=None, pattern=r"^[0-9]+\.[0-9]{2}$")
    payer_participant_id: ParticipantId | None = None
    split_config: dict[str, Any] | None = None
    reference_day: int | None = Field(default=None, ge=1, le=31)
    start_competence_month: str | None = Field(
        default=None,
        pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$",
    )
    end_competence_month: str | None = Field(
        default=None,
        pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$",
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Description cannot be blank.")
        return trimmed

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            amount_decimal = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Amount must be a decimal number.") from exc
        if amount_decimal <= Decimal("0"):
            raise ValueError("Amount must be greater than zero.")
        return value

    @model_validator(mode="after")
    def validate_has_changes(self) -> UpdateRecurrenceRequest:
        if len(self.model_fields_set - {"requested_by_participant_id"}) == 0:
            raise ValueError("At least one updatable field must be provided.")
        return self


class PauseRecurrenceRequest(BaseModel):
    """Payload to pause recurrence generation."""

    requested_by_participant_id: ParticipantId
    reason: str | None = Field(default=None, max_length=200)


class ReactivateRecurrenceRequest(BaseModel):
    """Payload to reactivate recurrence generation."""

    requested_by_participant_id: ParticipantId


class EndRecurrenceRequest(BaseModel):
    """Payload to end recurrence permanently."""

    requested_by_participant_id: ParticipantId
    end_competence_month: str | None = Field(
        default=None,
        pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$",
    )


class BlockedRecurrenceItemResponse(BaseModel):
    """Blocked recurrence detail returned by generation endpoint."""

    recurrence_id: UUID
    code: str
    message: str

    @classmethod
    def from_model(
        cls,
        item: BlockedRecurrenceItem,
    ) -> BlockedRecurrenceItemResponse:
        return cls(
            recurrence_id=item.recurrence_id,
            code=item.code,
            message=item.message,
        )


class GenerateRecurrencesResponse(BaseModel):
    """Response payload for monthly recurrence generation execution."""

    competence_month: str = Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")
    processed_rules: int = Field(ge=0)
    generated_count: int = Field(ge=0)
    ignored_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    blocked_items: list[BlockedRecurrenceItemResponse] = Field(default_factory=list)

    @classmethod
    def from_result(
        cls,
        result: GenerateRecurrencesResult,
        *,
        include_blocked_details: bool,
    ) -> GenerateRecurrencesResponse:
        blocked_items = (
            [
                BlockedRecurrenceItemResponse.from_model(item)
                for item in result.blocked_items
            ]
            if include_blocked_details
            else []
        )
        return cls(
            competence_month=format_competence_month(result.competence_month),
            processed_rules=result.processed_rules,
            generated_count=result.generated_count,
            ignored_count=result.ignored_count,
            blocked_count=result.blocked_count,
            failed_count=result.failed_count,
            blocked_items=blocked_items,
        )
