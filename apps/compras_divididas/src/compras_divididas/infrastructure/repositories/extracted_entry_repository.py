"""Repository adapter for extracted entry persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from compras_divididas.infrastructure.db.models.extracted_entry import (
    ExtractedEntryModel,
)


@dataclass(frozen=True, slots=True)
class ExtractedEntryCreate:
    """Input payload used to persist one extracted entry."""

    id: UUID
    run_id: UUID
    raw_message_id: UUID
    participant_id: UUID | None
    normalized_description: str | None
    amount_cents: int | None
    classification: str
    reason_code: str | None
    reason_message: str | None
    is_refund_keyword: bool
    dedupe_key: str | None
    dedupe_bucket_5m: int | None
    included_in_calculation: bool
    created_at: datetime


class ExtractedEntryRepository:
    """SQLAlchemy repository for extracted message entries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_many(
        self,
        payloads: list[ExtractedEntryCreate],
    ) -> list[ExtractedEntryModel]:
        """Insert extracted entries and flush session state."""
        rows = [
            ExtractedEntryModel(
                id=payload.id,
                run_id=payload.run_id,
                raw_message_id=payload.raw_message_id,
                participant_id=payload.participant_id,
                normalized_description=payload.normalized_description,
                amount_cents=payload.amount_cents,
                classification=payload.classification,
                reason_code=payload.reason_code,
                reason_message=payload.reason_message,
                is_refund_keyword=payload.is_refund_keyword,
                dedupe_key=payload.dedupe_key,
                dedupe_bucket_5m=payload.dedupe_bucket_5m,
                included_in_calculation=payload.included_in_calculation,
                created_at=payload.created_at,
            )
            for payload in payloads
        ]
        self._session.add_all(rows)
        self._session.flush()
        return rows
