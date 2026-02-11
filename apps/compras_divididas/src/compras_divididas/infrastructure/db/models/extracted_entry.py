"""ORM model for extracted and classified message entries."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from compras_divididas.infrastructure.db.session import Base


class ExtractedEntryModel(Base):
    """Extracted classification result persisted for one raw message."""

    __tablename__ = "extracted_entry"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("process_run.id"))
    raw_message_id: Mapped[UUID] = mapped_column(ForeignKey("raw_message.id"))
    participant_id: Mapped[UUID | None] = mapped_column(ForeignKey("participant.id"))
    normalized_description: Mapped[str | None] = mapped_column(Text)
    amount_cents: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(Text, default="BRL")
    classification: Mapped[str] = mapped_column(
        Enum("valid", "invalid", "ignored", "deduplicated", name="entry_classification")
    )
    reason_code: Mapped[str | None] = mapped_column(Text)
    reason_message: Mapped[str | None] = mapped_column(Text)
    is_refund_keyword: Mapped[bool] = mapped_column(Boolean, default=False)
    dedupe_key: Mapped[str | None] = mapped_column(Text)
    dedupe_bucket_5m: Mapped[int | None] = mapped_column(BigInteger)
    included_in_calculation: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
