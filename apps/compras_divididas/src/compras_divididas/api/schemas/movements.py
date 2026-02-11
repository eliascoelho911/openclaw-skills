"""Schemas for movement create endpoint."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from compras_divididas.db.models.financial_movement import FinancialMovement
from compras_divididas.domain.money import format_money

MovementKind = Literal["purchase", "refund"]


class CreateMovementRequest(BaseModel):
    """Payload for creating purchase/refund movements."""

    type: MovementKind
    amount: str = Field(pattern=r"^[0-9]+\.[0-9]{2}$")
    description: str = Field(min_length=1, max_length=280)
    occurred_at: datetime | None = None
    payer_participant_id: UUID | None = None
    requested_by_participant_id: UUID
    external_id: str | None = Field(default=None, max_length=120)
    original_purchase_id: UUID | None = None
    original_purchase_external_id: str | None = Field(default=None, max_length=120)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Description cannot be blank.")
        return trimmed

    @field_validator("external_id", "original_purchase_external_id")
    @classmethod
    def validate_optional_identifiers(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Identifier cannot be blank.")
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
    def validate_refund_reference(self) -> CreateMovementRequest:
        if self.type == "refund":
            if not (self.original_purchase_id or self.original_purchase_external_id):
                raise ValueError(
                    "Refund requires original_purchase_id or "
                    "original_purchase_external_id."
                )
            return self

        if self.original_purchase_id or self.original_purchase_external_id:
            raise ValueError("Purchase cannot reference an original purchase.")
        return self


class MovementResponse(BaseModel):
    """Serialized movement returned by API."""

    id: UUID
    type: MovementKind
    amount: str = Field(pattern=r"^-?[0-9]+\.[0-9]{2}$")
    description: str
    occurred_at: datetime
    competence_month: str = Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")
    payer_participant_id: UUID
    requested_by_participant_id: UUID
    external_id: str | None
    original_purchase_id: UUID | None
    created_at: datetime

    @classmethod
    def from_model(cls, movement: FinancialMovement) -> MovementResponse:
        return cls(
            id=movement.id,
            type=movement.movement_type.value,
            amount=format_money(movement.amount),
            description=movement.description,
            occurred_at=movement.occurred_at,
            competence_month=f"{movement.competence_month.year:04d}-{movement.competence_month.month:02d}",
            payer_participant_id=movement.payer_participant_id,
            requested_by_participant_id=movement.requested_by_participant_id,
            external_id=movement.external_id,
            original_purchase_id=movement.original_purchase_id,
            created_at=movement.created_at,
        )
