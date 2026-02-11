"""Participant persistence operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from compras_divididas.db.models.participant import Participant
from compras_divididas.domain.errors import DomainInvariantError


class ParticipantRepository:
    """Repository for active participants used by financial flows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_active_exactly_two(self) -> list[Participant]:
        statement = (
            select(Participant)
            .where(Participant.is_active.is_(True))
            .order_by(Participant.code.asc())
        )
        participants = list(self._session.scalars(statement).all())
        if len(participants) != 2:
            raise DomainInvariantError(
                message="Exactly two active participants are required.",
                details={"active_participants": len(participants)},
            )
        return participants
