import asyncio
import io
from PIL import Image
import pytesseract
from openai import AsyncOpenAI
import base64
from app.config import get_settings
from app.utils.language_utils import get_tesseract_lang
import structlog

logger = structlog.get_logger(__name__)


async def extract_text(file_bytes: bytes, mime_type: str, language: str) -> str:
    if mime_type == "application/pdf":
        return await _extract_from_pdf(file_bytes, language)
    return await _extract_from_image(file_bytes, mime_type, language)


async def _extract_from_image(file_bytes: bytes, mime_type: str, language: str) -> str:
    try:
        text = await _openai_vision_ocr(file_bytes, mime_type)
        if text and len(text.strip()) > 20:
            return text
    except Exception as exc:
        logger.warning("openai_ocr_failed", error=str(exc))

    return await asyncio.to_thread(_tesseract_ocr, file_bytes, language)


async def _extract_from_pdf(file_bytes: bytes, language: str) -> str:
    try:
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages_text = [page.extract_text() or "" for page in reader.pages]
        combined = "\n".join(pages_text).strip()
        if combined:
            return combined
    except Exception as exc:
        logger.warning("pdf_text_extract_failed", error=str(exc))

    return await asyncio.to_thread(_tesseract_ocr, file_bytes, language)


async def _openai_vision_ocr(file_bytes: bytes, mime_type: str) -> str:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    b64 = base64.b64encode(file_bytes).decode()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract all text from this medical document. "
                            "Return only the raw text, no formatting."
                        ),
                    },
                ],
            }
        ],
        max_tokens=2000,
    )
    return response.choices[0].message.content or ""


def _tesseract_ocr(file_bytes: bytes, language: str) -> str:
    lang = get_tesseract_lang(language)
    image = Image.open(io.BytesIO(file_bytes))
    return pytesseract.image_to_string(image, lang=lang)
