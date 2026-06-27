from datetime import datetime
from typing import Literal
from pydantic import BaseModel

EDocumentStatus = Literal["uploaded", "processing", "processed", "failed"]


class DocumentResponse(BaseModel):
    id: str
    user_id: str
    file_key: str
    original_name: str
    mime_type: str
    status: EDocumentStatus
    language: str
    ocr_text: str | None
    created_at: datetime

    @classmethod
    def from_doc(cls, doc: dict) -> "DocumentResponse":
        return cls(
            id=str(doc["_id"]),
            user_id=str(doc["user_id"]),
            file_key=doc["file_key"],
            original_name=doc["original_name"],
            mime_type=doc["mime_type"],
            status=doc.get("status", "uploaded"),
            language=doc.get("language", "hi"),
            ocr_text=doc.get("ocr_text"),
            created_at=doc["created_at"],
        )


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    presigned_url: str | None = None


class PaginatedDocuments(BaseModel):
    items: list[DocumentResponse]
    pagination: dict
