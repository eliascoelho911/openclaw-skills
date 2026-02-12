"""Pydantic schemas for participants endpoints."""

from __future__ import annotations

from typing import Annotated, Any, cast

from pydantic import BaseModel, Field

from compras_divididas.db.models.participant import Participant

PARTICIPANT_ID_ENUM = ["elias", "leticia"]
ParticipantId = Annotated[
    str,
    Field(
        json_schema_extra=cast(dict[str, Any], {"enum": PARTICIPANT_ID_ENUM}),
    ),
]


class ParticipantResponse(BaseModel):
    """Public participant representation."""

    id: ParticipantId
    display_name: str
    is_active: bool

    @classmethod
    def from_model(cls, participant: Participant) -> ParticipantResponse:
        return cls(
            id=str(participant.id),
            display_name=participant.display_name,
            is_active=participant.is_active,
        )


class ParticipantsListResponse(BaseModel):
    """Participants list payload."""

    participants: list[ParticipantResponse]

    @classmethod
    def from_models(cls, participants: list[Participant]) -> ParticipantsListResponse:
        return cls(
            participants=[ParticipantResponse.from_model(item) for item in participants]
        )
