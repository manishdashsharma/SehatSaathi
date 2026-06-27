import uuid
from pathlib import Path

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


def generate_file_key(user_id: str, original_name: str) -> str:
    ext = Path(original_name).suffix.lower()
    return f"documents/{user_id}/{uuid.uuid4()}{ext}"


def is_allowed_mime(mime_type: str) -> bool:
    return mime_type in ALLOWED_MIME_TYPES


def is_allowed_size(size_bytes: int) -> bool:
    return size_bytes <= MAX_FILE_SIZE_BYTES
