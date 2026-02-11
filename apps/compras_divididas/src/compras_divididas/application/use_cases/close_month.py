"""Use case for monthly closure reconciliation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from re import search
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from compras_divididas.application.services.settlement_service import (
    calculate_settlement,
)
from compras_divididas.domain.value_objects import MoneyBRL


class ParticipantCountError(ValueError):
    """Raised when closure is attempted with invalid participant count."""


class PeriodInput(BaseModel):
    """Input period for closure creation."""

    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


class ParticipantInput(BaseModel):
    """Participant payload received by adapters."""

    external_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)


class MessageInput(BaseModel):
    """Raw message payload received by adapters."""

    message_id: str | None = None
    author_external_id: str = Field(min_length=1)
    author_display_name: str = Field(min_length=1)
    content: str = Field(min_length=1)
    sent_at: datetime | None = None


class CloseMonthRequest(BaseModel):
    """Command payload for monthly closure."""

    period: PeriodInput
    participants: list[ParticipantInput] = Field(min_length=2, max_length=2)
    messages: list[MessageInput] = Field(min_length=1)
    source: str = "manual_copy"
    reprocess_mode: str = "new_version"


class ParticipantSummary(BaseModel):
    """Participant metadata included in the report."""

    external_id: str
    display_name: str


class ParticipantTotal(BaseModel):
    """Participant total amount in cents and BRL."""

    external_id: str
    total_cents: int
    total_brl: str


class TransferInstruction(BaseModel):
    """Final payment transfer instruction."""

    payer_external_id: str | None
    receiver_external_id: str | None
    amount_cents: int = Field(ge=0)
    amount_brl: str
    message: str


class ReconciliationCounts(BaseModel):
    """Counts summary by reconciliation status."""

    valid: int = Field(ge=0)
    invalid: int = Field(ge=0)
    ignored: int = Field(ge=0)
    deduplicated: int = Field(ge=0)


class MonthlyClosureReport(BaseModel):
    """Closure report returned by use case and adapters."""

    closure_id: UUID
    run_id: UUID
    status: str = "finalized"
    created_at: datetime
    period: PeriodInput
    participants: list[ParticipantSummary] = Field(min_length=2, max_length=2)
    totals_by_participant: list[ParticipantTotal] = Field(min_length=2, max_length=2)
    transfer_instruction: TransferInstruction
    counts: ReconciliationCounts
    valid_entries: list[dict[str, object]] = Field(default_factory=list)
    rejected_entries: list[dict[str, object]] = Field(default_factory=list)
    deduplicated_entries: list[dict[str, object]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MonthlyClosureWriter(Protocol):
    """Persistence port for closure reports."""

    def save(self, report: MonthlyClosureReport) -> None:
        """Persist closure report data."""


class InMemoryMonthlyClosureWriter:
    """In-memory closure persistence used by MVP adapters."""

    def __init__(self) -> None:
        self.reports: list[MonthlyClosureReport] = []

    def save(self, report: MonthlyClosureReport) -> None:
        self.reports.append(report)


class CloseMonthUseCase:
    """Generate a monthly closure report from raw messages."""

    def __init__(
        self,
        closure_writer: MonthlyClosureWriter | None = None,
        *,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._closure_writer = closure_writer or InMemoryMonthlyClosureWriter()
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def execute(self, request: CloseMonthRequest) -> MonthlyClosureReport:
        """Process valid monthly entries and return transfer instruction."""
        if len(request.participants) != 2:
            raise ParticipantCountError(
                "Monthly closure requires exactly two participants"
            )

        participant_a = request.participants[0]
        participant_b = request.participants[1]
        if participant_a.external_id == participant_b.external_id:
            raise ParticipantCountError("Participants must have distinct external ids")

        totals_by_external_id: dict[str, int] = {
            participant_a.external_id: 0,
            participant_b.external_id: 0,
        }

        valid_count = 0
        invalid_count = 0
        ignored_count = 0
        for message in request.messages:
            amount_cents = _extract_amount_cents(message.content)
            if message.author_external_id not in totals_by_external_id:
                ignored_count += 1
                continue
            if amount_cents is None:
                ignored_count += 1
                continue
            if amount_cents <= 0:
                invalid_count += 1
                continue
            totals_by_external_id[message.author_external_id] += amount_cents
            valid_count += 1

        settlement = calculate_settlement(
            participant_a_external_id=participant_a.external_id,
            total_a_cents=totals_by_external_id[participant_a.external_id],
            participant_b_external_id=participant_b.external_id,
            total_b_cents=totals_by_external_id[participant_b.external_id],
        )

        created_at = self._now_provider()
        run_id = uuid4()
        closure_id = uuid4()
        report = MonthlyClosureReport(
            closure_id=closure_id,
            run_id=run_id,
            created_at=created_at,
            period=request.period,
            participants=[
                ParticipantSummary(
                    external_id=participant_a.external_id,
                    display_name=participant_a.display_name,
                ),
                ParticipantSummary(
                    external_id=participant_b.external_id,
                    display_name=participant_b.display_name,
                ),
            ],
            totals_by_participant=[
                ParticipantTotal(
                    external_id=participant_a.external_id,
                    total_cents=totals_by_external_id[participant_a.external_id],
                    total_brl=MoneyBRL(
                        cents=totals_by_external_id[participant_a.external_id]
                    ).to_brl(),
                ),
                ParticipantTotal(
                    external_id=participant_b.external_id,
                    total_cents=totals_by_external_id[participant_b.external_id],
                    total_brl=MoneyBRL(
                        cents=totals_by_external_id[participant_b.external_id]
                    ).to_brl(),
                ),
            ],
            transfer_instruction=TransferInstruction(
                payer_external_id=settlement.payer_external_id,
                receiver_external_id=settlement.receiver_external_id,
                amount_cents=settlement.transfer_amount_cents,
                amount_brl=MoneyBRL(cents=settlement.transfer_amount_cents).to_brl(),
                message=settlement.message,
            ),
            counts=ReconciliationCounts(
                valid=valid_count,
                invalid=invalid_count,
                ignored=ignored_count,
                deduplicated=0,
            ),
            warnings=[],
        )
        self._closure_writer.save(report)
        return report


def hash_input_payload(request: CloseMonthRequest) -> str:
    """Build deterministic hash for idempotency checks."""
    serialized_payload = request.model_dump_json(by_alias=True, exclude_none=False)
    return sha256(serialized_payload.encode("utf-8")).hexdigest()


def _extract_amount_cents(content: str) -> int | None:
    match = search(r"-?\d+(?:[\.,]\d{1,2})?", content)
    if match is None:
        return None

    normalized = match.group(0).replace(",", ".")
    try:
        decimal_value = Decimal(normalized)
    except InvalidOperation:
        return None

    return MoneyBRL.from_decimal(decimal_value).cents
