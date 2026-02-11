"""Repository ports for the reconciliation core."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from compras_divididas.domain.value_objects import Period


@dataclass(frozen=True, slots=True)
class ParticipantRecord:
    """Participant data required by application services."""

    id: UUID
    external_id: str
    display_name: str


@dataclass(frozen=True, slots=True)
class ProcessRunRecord:
    """Persisted process run metadata."""

    id: UUID
    period: Period
    input_hash: str
    source_type: str
    prompt_version: str
    schema_version: str
    status: str
    created_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class RawMessageRecord:
    """Raw input message persisted for auditability."""

    id: UUID
    run_id: UUID
    source_message_id: str | None
    author_external_id: str
    author_display_name: str
    content: str
    sent_at: datetime | None
    inferred_month: bool


class ParticipantRepository(Protocol):
    """Port for participant persistence and lookup."""

    def upsert_many(
        self, participants: list[ParticipantRecord]
    ) -> list[ParticipantRecord]:
        """Insert or update participants and return persisted values."""

    def list_by_external_ids(self, external_ids: list[str]) -> list[ParticipantRecord]:
        """Return participants matched by external ids."""


class ProcessRunRepository(Protocol):
    """Port for process run persistence."""

    def get_by_input_hash(
        self, period: Period, input_hash: str
    ) -> ProcessRunRecord | None:
        """Fetch an existing process run by period and hash."""

    def create(self, run: ProcessRunRecord) -> ProcessRunRecord:
        """Persist a new process run."""

    def update_status(
        self, run_id: UUID, status: str, completed_at: datetime | None
    ) -> None:
        """Update run processing status and optional completion timestamp."""


class RawMessageRepository(Protocol):
    """Port for raw message persistence."""

    def create_many(self, messages: list[RawMessageRecord]) -> list[RawMessageRecord]:
        """Persist raw messages and return stored records."""
