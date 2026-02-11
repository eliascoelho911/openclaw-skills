"""ORM model for closure line items."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from compras_divididas.infrastructure.db.session import Base


class ClosureLineItemModel(Base):
    """Detailed closure line item linked to one extracted entry."""

    __tablename__ = "closure_line_item"
    __table_args__ = (
        UniqueConstraint(
            "closure_id",
            "entry_id",
            name="uq_closure_line_item_closure_entry",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    closure_id: Mapped[UUID] = mapped_column(ForeignKey("monthly_closure.id"))
    entry_id: Mapped[UUID] = mapped_column(ForeignKey("extracted_entry.id"))
    display_order: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
