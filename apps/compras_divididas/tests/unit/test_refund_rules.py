from compras_divididas.application.schemas.classification import (
    ClassifiedEntry,
    EntryClassification,
)
from compras_divididas.domain.services.reconciliation_rules import (
    apply_dedupe,
    has_refund_keyword,
    validate_refund_amount,
)


def test_refund_keyword_detection() -> None:
    assert has_refund_keyword("Extorno do mercado -20")
    assert has_refund_keyword("reembolso farmacia")
    assert not has_refund_keyword("mercado -20")


def test_negative_amount_requires_refund_keyword() -> None:
    valid, reason = validate_refund_amount(-2000, "mercado -20")
    assert not valid
    assert reason == "negative_without_refund_keyword"

    valid_with_keyword, keyword_reason = validate_refund_amount(
        -2000,
        "extorno mercado -20",
    )
    assert valid_with_keyword
    assert keyword_reason is None


def test_dedupe_marks_second_entry_in_same_window() -> None:
    first = ClassifiedEntry(
        message_id="m1",
        author_external_id="elias",
        author_display_name="Elias",
        content="mercado 20",
        normalized_description="mercado",
        amount_cents=2000,
        classification=EntryClassification.VALID,
        dedupe_key="elias|mercado|2000",
        dedupe_bucket_5m=100,
        included_in_calculation=True,
    )
    second = ClassifiedEntry(
        message_id="m2",
        author_external_id="elias",
        author_display_name="Elias",
        content="mercado 20",
        normalized_description="mercado",
        amount_cents=2000,
        classification=EntryClassification.VALID,
        dedupe_key="elias|mercado|2000",
        dedupe_bucket_5m=100,
        included_in_calculation=True,
    )

    deduped = apply_dedupe([first, second])

    assert deduped[0].classification == EntryClassification.VALID
    assert deduped[1].classification == EntryClassification.DEDUPLICATED
    assert deduped[1].included_in_calculation is False
    assert deduped[1].duplicated_of_entry_id == deduped[0].entry_id
