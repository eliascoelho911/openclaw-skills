"""Recurrence rule service layer."""

from __future__ import annotations

from typing import Protocol


class SessionProtocol(Protocol):
    """Subset of SQLAlchemy session APIs used by recurrence service."""

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class RecurrenceService:
    """Coordinates recurrence rule use cases."""

    def __init__(self, *, session: SessionProtocol) -> None:
        self._session = session
