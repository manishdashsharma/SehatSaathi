from datetime import datetime
from typing import Literal
from pydantic import BaseModel, field_validator
import re

ELanguage = Literal["hi", "en", "mr", "bn", "ta"]
EUserRole = Literal["user", "doctor_reviewer", "moderator", "superadmin"]


class RegisterRequest(BaseModel):
    phone: str
    name: str
    language: ELanguage = "hi"

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"\D", "", v)
        if len(cleaned) != 10:
            raise ValueError("Phone must be 10 digits")
        return cleaned


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ConsentRequest(BaseModel):
    given: bool


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    language: ELanguage | None = None


class LocationUpdate(BaseModel):
    lat: float
    lng: float
    village: str | None = None
    district: str | None = None
    state: str | None = None


class UserResponse(BaseModel):
    id: str
    phone: str
    name: str
    language: str
    role: str
    consent_given: bool
    upload_count: int
    call_count: int
    is_active: bool
    created_at: datetime

    @classmethod
    def from_doc(cls, doc: dict) -> "UserResponse":
        return cls(
            id=str(doc["_id"]),
            phone=doc["phone"],
            name=doc["name"],
            language=doc.get("language", "hi"),
            role=doc.get("role", "user"),
            consent_given=doc.get("consent_given", False),
            upload_count=doc.get("upload_count", 0),
            call_count=doc.get("call_count", 0),
            is_active=doc.get("is_active", True),
            created_at=doc["created_at"],
        )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
