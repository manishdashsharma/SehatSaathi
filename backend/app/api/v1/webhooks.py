import hashlib
import hmac
import json
from fastapi import APIRouter, BackgroundTasks, Header, Request
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.guardrails.emergency_detector import is_emergency
from app.models import session as session_model
from app.models import emergency_contact as ec_model
from app.models import user as user_model
from app.services import email_service
from app.utils.response_utils import success_response
import structlog

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = structlog.get_logger(__name__)


@router.post("/livekit")
async def livekit_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
) -> JSONResponse:
    body = await request.body()
    settings = get_settings()

    if not _verify_livekit_signature(body, authorization, settings.livekit_api_secret):
        return JSONResponse(status_code=401, content={"error": "Invalid signature"})

    event = json.loads(body)
    event_type = event.get("event")

    if event_type == "room_finished":
        room_name = event.get("room", {}).get("name")
        if room_name:
            background_tasks.add_task(_handle_room_finished, room_name)

    return success_response({"received": True})


async def _handle_room_finished(room_name: str) -> None:
    session = await session_model.find_session_by_room(room_name)
    if not session or session.get("status") == "completed":
        return

    await session_model.end_session(str(session["_id"]))
    logger.info("session_auto_ended", room=room_name)


async def _check_and_alert_emergency(
    session_id: str, user_id: str, transcript: str
) -> None:
    flagged, score = is_emergency(transcript)
    if not flagged:
        return

    await session_model.flag_emergency(session_id)

    contacts = await ec_model.find_contacts_by_user(user_id)
    if not contacts:
        logger.warning("emergency_no_contacts", session_id=session_id)
        return

    user = await user_model.find_user_by_id(user_id)
    for contact in contacts:
        await email_service.send_emergency_alert(
            doctor_email=contact["doctor_email"],
            doctor_name=contact.get("doctor_name", "Doctor"),
            patient_name=user.get("name", "Unknown") if user else "Unknown",
            patient_phone=user.get("phone", "") if user else "",
            session_id=session_id,
            emergency_score=score,
            transcript_excerpt=transcript[:500],
        )


def _verify_livekit_signature(
    body: bytes, authorization: str | None, api_secret: str
) -> bool:
    if not authorization:
        return False
    expected = hmac.new(api_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(authorization, expected)

