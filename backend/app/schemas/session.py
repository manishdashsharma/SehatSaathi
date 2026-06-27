from datetime import datetime
from typing import Literal
from pydantic import BaseModel

ESessionStatus = Literal["active", "completed", "flagged"]


class StartSessionRequest(BaseModel):
    document_id: str
    language: str = "hi"


class EndSessionRequest(BaseModel):
    transcript: str | None = None


class SessionResponse(BaseModel):
    id: str
    user_id: str
    document_id: str
    livekit_room: str
    livekit_token: str | None
    status: ESessionStatus
    language: str
    emergency_flagged: bool
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime

    @classmethod
    def from_doc(cls, doc: dict, livekit_token: str | None = None) -> "SessionResponse":
        return cls(
            id=str(doc["_id"]),
            user_id=str(doc["user_id"]),
            document_id=str(doc["document_id"]),
            livekit_room=doc["livekit_room"],
            livekit_token=livekit_token,
            status=doc.get("status", "active"),
            language=doc.get("language", "hi"),
            emergency_flagged=doc.get("emergency_flagged", False),
            started_at=doc["started_at"],
            ended_at=doc.get("ended_at"),
            created_at=doc["created_at"],
        )


class PaginatedSessions(BaseModel):
    items: list[SessionResponse]
    pagination: dict
