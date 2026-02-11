"""Schemas and enums for message classification pipeline."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EntryClassification(StrEnum):
    """Possible outcomes for message reconciliation."""

    VALID = "valid"
    INVALID = "invalid"
    IGNORED = "ignored"
    DEDUPLICATED = "deduplicated"


class ReasonCode(StrEnum):
    """Reason codes used for rejected or deduplicated entries."""

    UNKNOWN_PARTICIPANT = "unknown_participant"
    NON_FINANCIAL = "non_financial"
    MISSING_AMOUNT = "missing_amount"
    ZERO_AMOUNT = "zero_amount"
    NEGATIVE_WITHOUT_REFUND_KEYWORD = "negative_without_refund_keyword"
    DUPLICATED_IN_WINDOW = "duplicated_in_5m_window"
    OUT_OF_PERIOD = "out_of_period"
    LLM_FALLBACK = "llm_fallback"


class ClassifiedEntry(BaseModel):
    """Normalized classification output for one message."""

    entry_id: UUID = Field(default_factory=uuid4)
    message_id: str
    author_external_id: str
    author_display_name: str
    content: str
    sent_at: datetime | None = None
    inferred_month: bool = False
    normalized_description: str | None = None
    amount_cents: int | None = None
    classification: EntryClassification
    reason_code: str | None = None
    reason_message: str | None = None
    is_refund_keyword: bool = False
    dedupe_key: str | None = None
    dedupe_bucket_5m: int | None = None
    included_in_calculation: bool
    duplicated_of_entry_id: UUID | None = None
