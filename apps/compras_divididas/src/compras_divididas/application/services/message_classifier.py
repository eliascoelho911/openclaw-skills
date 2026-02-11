"""Hybrid message classifier using deterministic rules plus optional LLM."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from re import search
from typing import Protocol

from compras_divididas.application.schemas.classification import (
    ClassifiedEntry,
    EntryClassification,
    ReasonCode,
)
from compras_divididas.domain.services.reconciliation_rules import (
    compute_dedupe_bucket_5m,
    compute_dedupe_key,
    normalize_description_for_dedupe,
    validate_refund_amount,
)
from compras_divididas.domain.value_objects import MoneyBRL
from compras_divididas.infrastructure.llm.openai_classifier import MessageClassification

PURCHASE_HINTS = (
    "mercado",
    "farmacia",
    "padaria",
    "acougue",
    "compra",
    "ifood",
    "uber",
    "gasolina",
    "internet",
    "luz",
)


class LLMMessageClassifier(Protocol):
    """Protocol for LLM-backed message classification."""

    def classify_message(
        self, message_text: str, author_external_id: str
    ) -> MessageClassification:
        """Classify one raw message into structured output."""
        ...


def extract_amount_cents(content: str) -> int | None:
    """Extract BRL amount from free-text messages."""
    match = search(r"-?\d+(?:[\.,]\d{1,2})?", content)
    if match is None:
        return None

    normalized = match.group(0).replace(",", ".")
    try:
        decimal_value = Decimal(normalized)
    except InvalidOperation:
        return None
    return MoneyBRL.from_decimal(decimal_value).cents


def normalize_description(content: str) -> str:
    """Normalize description by removing currency marker and first amount token."""
    without_currency = content.replace("R$", " ").replace("r$", " ")
    without_amount = search(r"-?\d+(?:[\.,]\d{1,2})?", without_currency)
    if without_amount is None:
        return " ".join(without_currency.split()).strip()
    start, end = without_amount.span()
    cleaned = f"{without_currency[:start]} {without_currency[end:]}"
    return " ".join(cleaned.split()).strip()


def is_non_financial_message(content: str) -> bool:
    """Check whether message has no strong purchase signal."""
    lowered = content.lower()
    return not any(hint in lowered for hint in PURCHASE_HINTS)


class HybridMessageClassifier:
    """Classify messages with deterministic rules and optional LLM fallback."""

    def __init__(self, llm_classifier: LLMMessageClassifier | None = None) -> None:
        self._llm_classifier = llm_classifier

    def classify_message(
        self,
        *,
        message_id: str | None,
        author_external_id: str,
        author_display_name: str,
        content: str,
        sent_at: datetime | None,
        participant_external_ids: set[str],
        period_year: int,
        period_month: int,
        now: datetime,
    ) -> ClassifiedEntry:
        """Classify one message and return normalized metadata."""
        normalized_message_id = message_id or (
            f"generated-{sha256(content.encode('utf-8')).hexdigest()[:12]}"
        )
        inferred_month = sent_at is None

        if author_external_id not in participant_external_ids:
            return ClassifiedEntry(
                message_id=normalized_message_id,
                author_external_id=author_external_id,
                author_display_name=author_display_name,
                content=content,
                sent_at=sent_at,
                inferred_month=inferred_month,
                classification=EntryClassification.IGNORED,
                reason_code=ReasonCode.UNKNOWN_PARTICIPANT.value,
                reason_message="Author is outside the bilateral participant set.",
                included_in_calculation=False,
            )

        if sent_at is not None and (
            sent_at.year != period_year or sent_at.month != period_month
        ):
            return ClassifiedEntry(
                message_id=normalized_message_id,
                author_external_id=author_external_id,
                author_display_name=author_display_name,
                content=content,
                sent_at=sent_at,
                inferred_month=False,
                classification=EntryClassification.IGNORED,
                reason_code=ReasonCode.OUT_OF_PERIOD.value,
                reason_message="Message date is outside the selected period.",
                included_in_calculation=False,
            )

        amount_cents = extract_amount_cents(content)
        normalized_description = normalize_description(content)
        if amount_cents is None and self._llm_classifier is not None:
            llm_result = self._llm_classifier.classify_message(
                content, author_external_id
            )
            amount_cents = llm_result.amount_cents
            normalized_description = llm_result.description or normalized_description
            if llm_result.classification == EntryClassification.IGNORED.value:
                return ClassifiedEntry(
                    message_id=normalized_message_id,
                    author_external_id=author_external_id,
                    author_display_name=author_display_name,
                    content=content,
                    sent_at=sent_at,
                    inferred_month=inferred_month,
                    normalized_description=normalized_description or None,
                    amount_cents=amount_cents,
                    classification=EntryClassification.IGNORED,
                    reason_code=llm_result.reason_code or ReasonCode.LLM_FALLBACK.value,
                    reason_message=llm_result.reason_message
                    or "Ignored by LLM classification.",
                    included_in_calculation=False,
                    is_refund_keyword=llm_result.is_refund_keyword,
                )

        if amount_cents is None:
            classification = (
                EntryClassification.IGNORED
                if is_non_financial_message(content)
                else EntryClassification.INVALID
            )
            reason_code = (
                ReasonCode.NON_FINANCIAL.value
                if classification == EntryClassification.IGNORED
                else ReasonCode.MISSING_AMOUNT.value
            )
            reason_message = (
                "Message ignored because no financial context was detected."
                if classification == EntryClassification.IGNORED
                else "Message does not contain an identifiable monetary value."
            )
            return ClassifiedEntry(
                message_id=normalized_message_id,
                author_external_id=author_external_id,
                author_display_name=author_display_name,
                content=content,
                sent_at=sent_at,
                inferred_month=inferred_month,
                classification=classification,
                reason_code=reason_code,
                reason_message=reason_message,
                included_in_calculation=False,
            )

        if amount_cents == 0:
            return ClassifiedEntry(
                message_id=normalized_message_id,
                author_external_id=author_external_id,
                author_display_name=author_display_name,
                content=content,
                sent_at=sent_at,
                inferred_month=inferred_month,
                normalized_description=normalized_description or None,
                amount_cents=amount_cents,
                classification=EntryClassification.INVALID,
                reason_code=ReasonCode.ZERO_AMOUNT.value,
                reason_message="Amount must be different from zero.",
                included_in_calculation=False,
            )

        refund_allowed, reason = validate_refund_amount(amount_cents, content)
        if not refund_allowed:
            return ClassifiedEntry(
                message_id=normalized_message_id,
                author_external_id=author_external_id,
                author_display_name=author_display_name,
                content=content,
                sent_at=sent_at,
                inferred_month=inferred_month,
                normalized_description=normalized_description or None,
                amount_cents=amount_cents,
                classification=EntryClassification.INVALID,
                reason_code=reason,
                reason_message="Negative amount requires an explicit refund keyword.",
                included_in_calculation=False,
            )

        normalized_for_dedupe = normalize_description_for_dedupe(normalized_description)
        return ClassifiedEntry(
            message_id=normalized_message_id,
            author_external_id=author_external_id,
            author_display_name=author_display_name,
            content=content,
            sent_at=sent_at,
            inferred_month=inferred_month,
            normalized_description=normalized_for_dedupe,
            amount_cents=amount_cents,
            classification=EntryClassification.VALID,
            is_refund_keyword=amount_cents < 0,
            dedupe_key=compute_dedupe_key(
                author_external_id,
                normalized_for_dedupe,
                amount_cents,
            ),
            dedupe_bucket_5m=compute_dedupe_bucket_5m(sent_at, now=now),
            included_in_calculation=True,
        )
