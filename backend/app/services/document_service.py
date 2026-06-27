import asyncio
import io
from fastapi import UploadFile
from app.config import get_settings
from app.core.exceptions import NotFoundError, StorageError, ValidationError
from app.database import get_minio
from app.models import document as document_model
from app.services import ocr_service
from app.services import user_service
from app.utils.file_utils import generate_file_key, is_allowed_mime, is_allowed_size
import structlog

logger = structlog.get_logger(__name__)


async def upload_document(user: dict, file: UploadFile) -> dict:
    await user_service.increment_upload_count(str(user["_id"]))

    if not is_allowed_mime(file.content_type or ""):
        raise ValidationError(f"File type not allowed: {file.content_type}")

    file_bytes = await file.read()
    if not is_allowed_size(len(file_bytes)):
        raise ValidationError("File size exceeds 10MB limit")

    user_id = str(user["_id"])
    language = user.get("language", "hi")
    file_key = generate_file_key(user_id, file.filename or "upload")

    await _upload_to_minio(file_key, file_bytes, file.content_type or "application/octet-stream")

    doc = await document_model.create_document({
        "user_id": user_id,
        "file_key": file_key,
        "original_name": file.filename or "upload",
        "mime_type": file.content_type or "application/octet-stream",
        "status": "uploaded",
        "language": language,
        "ocr_text": None,
    })

    asyncio.create_task(
        _process_document(str(doc["_id"]), file_bytes, file.content_type or "", language)
    )

    return doc


async def _upload_to_minio(file_key: str, file_bytes: bytes, content_type: str) -> None:
    settings = get_settings()
    minio = get_minio()
    try:
        await asyncio.to_thread(
            minio.upload_fileobj,
            io.BytesIO(file_bytes),
            settings.minio_bucket,
            file_key,
            ExtraArgs={"ContentType": content_type},
        )
    except Exception as exc:
        logger.error("minio_upload_failed", error=str(exc))
        raise StorageError("Failed to upload file")


async def _process_document(
    document_id: str, file_bytes: bytes, mime_type: str, language: str
) -> None:
    await document_model.update_document(document_id, {"status": "processing"})
    try:
        ocr_text = await ocr_service.extract_text(file_bytes, mime_type, language)
        await document_model.update_document(
            document_id, {"status": "processed", "ocr_text": ocr_text}
        )
        logger.info("document_processed", document_id=document_id)
    except Exception as exc:
        logger.error("document_processing_failed", document_id=document_id, error=str(exc))
        await document_model.update_document(document_id, {"status": "failed"})


async def get_document(document_id: str, user_id: str) -> dict:
    doc = await document_model.find_document_by_id(document_id)
    if not doc:
        raise NotFoundError("Document")
    if str(doc["user_id"]) != user_id:
        raise NotFoundError("Document")
    return doc


async def list_documents(user_id: str, page: int = 1, limit: int = 20) -> dict:
    skip = (page - 1) * limit
    total, docs = await document_model.list_documents(user_id, skip=skip, limit=limit)
    return {
        "items": docs,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "has_next_page": skip + len(docs) < total,
        },
    }


async def get_presigned_url(document_id: str, user_id: str) -> str:
    doc = await get_document(document_id, user_id)
    settings = get_settings()
    minio = get_minio()
    try:
        url = await asyncio.to_thread(
            minio.generate_presigned_url,
            "get_object",
            Params={"Bucket": settings.minio_bucket, "Key": doc["file_key"]},
            ExpiresIn=3600,
        )
        return url
    except Exception as exc:
        logger.error("presigned_url_failed", error=str(exc))
        raise StorageError("Failed to generate file URL")
