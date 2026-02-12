"""Pydantic schemas for participants endpoints."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from compras_divididas.db.models.participant import Participant


class ParticipantResponse(BaseModel):
    """Public participant representation."""

    id: UUID
    code: str
    display_name: str

    @classmethod
    def from_model(cls, participant: Participant) -> ParticipantResponse:
        return cls(
            id=participant.id,
            code=participant.code,
            display_name=participant.display_name,
        )


class ParticipantsListResponse(BaseModel):
    """Participants list payload."""

    participants: list[ParticipantResponse]

    @classmethod
    def from_models(cls, participants: list[Participant]) -> ParticipantsListResponse:
        return cls(
            participants=[ParticipantResponse.from_model(item) for item in participants]
        )
