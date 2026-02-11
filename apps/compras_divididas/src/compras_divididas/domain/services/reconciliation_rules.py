"""Domain rules for refunds and duplicate detection."""

from __future__ import annotations

from datetime import UTC, datetime
from re import sub

from compras_divididas.application.schemas.classification import (
    ClassifiedEntry,
    EntryClassification,
    ReasonCode,
)

REFUND_KEYWORDS = ("extorno", "reembolso", "cancelar", "deletar")


def has_refund_keyword(content: str) -> bool:
    """Return whether text contains an explicit refund keyword."""
    lowered = content.lower()
    return any(keyword in lowered for keyword in REFUND_KEYWORDS)


def validate_refund_amount(amount_cents: int, content: str) -> tuple[bool, str | None]:
    """Validate if a negative amount can be accepted as refund."""
    if amount_cents >= 0:
        return True, None
    if has_refund_keyword(content):
        return True, None
    return False, ReasonCode.NEGATIVE_WITHOUT_REFUND_KEYWORD.value


def normalize_description_for_dedupe(description: str) -> str:
    """Normalize descriptions to deterministic dedupe-safe text."""
    lowered = description.lower().strip()
    alphanumeric = sub(r"[^a-z0-9\s]", " ", lowered)
    collapsed = sub(r"\s+", " ", alphanumeric)
    return collapsed.strip()


def compute_dedupe_key(
    author_external_id: str,
    normalized_description: str | None,
    amount_cents: int | None,
) -> str | None:
    """Build dedupe key based on author, description, and amount."""
    if normalized_description is None or amount_cents is None:
        return None
    if normalized_description == "":
        return None
    return f"{author_external_id}|{normalized_description}|{amount_cents}"


def compute_dedupe_bucket_5m(sent_at: datetime | None, *, now: datetime) -> int:
    """Return 5-minute bucket index using message timestamp or fallback now."""
    reference = sent_at or now
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    unix_seconds = int(reference.timestamp())
    return unix_seconds // 300


def apply_dedupe(entries: list[ClassifiedEntry]) -> list[ClassifiedEntry]:
    """Mark duplicated valid entries in the same 5-minute bucket."""
    seen: dict[tuple[str, int], ClassifiedEntry] = {}
    updated: list[ClassifiedEntry] = []
    for entry in entries:
        if (
            entry.classification != EntryClassification.VALID
            or not entry.included_in_calculation
            or entry.dedupe_key is None
            or entry.dedupe_bucket_5m is None
        ):
            updated.append(entry)
            continue

        dedupe_signature = (entry.dedupe_key, entry.dedupe_bucket_5m)
        first_seen = seen.get(dedupe_signature)
        if first_seen is None:
            seen[dedupe_signature] = entry
            updated.append(entry)
            continue

        deduplicated_entry = entry.model_copy(
            update={
                "classification": EntryClassification.DEDUPLICATED,
                "reason_code": ReasonCode.DUPLICATED_IN_WINDOW.value,
                "reason_message": "Entry deduplicated in a 5-minute window.",
                "included_in_calculation": False,
                "duplicated_of_entry_id": first_seen.entry_id,
            }
        )
        updated.append(deduplicated_entry)
    return updated
