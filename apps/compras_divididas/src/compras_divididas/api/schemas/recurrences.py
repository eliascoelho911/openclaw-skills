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
