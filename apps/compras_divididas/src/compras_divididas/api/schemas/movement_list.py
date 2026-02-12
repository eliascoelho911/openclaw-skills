"""Schemas for movement listing endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field

from compras_divididas.api.schemas.movements import MovementResponse
from compras_divididas.db.models.financial_movement import FinancialMovement


class MovementListResponse(BaseModel):
    """Paginated movement list response."""

    items: list[MovementResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)

    @classmethod
    def from_models(
        cls,
        *,
        items: list[FinancialMovement],
        total: int,
        limit: int,
        offset: int,
    ) -> MovementListResponse:
        return cls(
            items=[MovementResponse.from_model(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )
