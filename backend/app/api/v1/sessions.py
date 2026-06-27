import asyncio
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from app.core.dependencies import get_current_user
from app.core.exceptions import AppException, ForbiddenError, NotFoundError
from app.models import session as session_model, agent_verdict as verdict_model
from app.schemas.session import EndSessionRequest, SessionResponse, StartSessionRequest
from app.services import livekit_service, user_service
from app.services.agent_orchestrator import get_verdicts
from app.agents.voice_agent import run_voice_agent
from app.utils.response_utils import error_response, success_response
import structlog

router = APIRouter(prefix="/sessions", tags=["sessions"])
logger = structlog.get_logger(__name__)


@router.post("/start")
async def start_session(
    body: StartSessionRequest,
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    try:
        if not current_user.get("consent_given"):
            raise ForbiddenError("Consent required before starting a session")

        await user_service.increment_call_count(str(current_user["_id"]))

        room_name = livekit_service.generate_room_name()
        await livekit_service.create_room(room_name)

        participant_identity = str(current_user["_id"])
        user_token = livekit_service.generate_user_token(room_name, participant_identity)

        session = await session_model.create_session({
            "user_id": str(current_user["_id"]),
            "document_id": body.document_id,
            "livekit_room": room_name,
            "language": body.language or current_user.get("language", "hi"),
        })

        verdicts = await get_verdicts(body.document_id)
        asyncio.create_task(
            run_voice_agent(room_name, verdicts, body.language or current_user.get("language", "hi"))
        )

        logger.info(
            "session_started",
            session_id=str(session["_id"]),
            user_id=str(current_user["_id"]),
        )
        return success_response(
            SessionResponse.from_doc(session, livekit_token=user_token).model_dump(),
            status_code=201,
        )
    except AppException as exc:
        return error_response(exc.message, exc.status_code)


@router.post("/{session_id}/end")
async def end_session(
    session_id: str,
    body: EndSessionRequest,
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    try:
        session = await session_model.find_session_by_id(session_id)
        if not session:
            raise NotFoundError("Session")
        if str(session["user_id"]) != str(current_user["_id"]):
            raise NotFoundError("Session")

        updated = await session_model.end_session(session_id, transcript=body.transcript)
        asyncio.create_task(livekit_service.delete_room(session["livekit_room"]))

        return success_response(SessionResponse.from_doc(updated).model_dump())
    except AppException as exc:
        return error_response(exc.message, exc.status_code)


@router.get("/")
async def list_sessions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    try:
        skip = (page - 1) * limit
        total, sessions = await session_model.list_sessions(
            str(current_user["_id"]), skip=skip, limit=limit
        )
        return success_response({
            "items": [SessionResponse.from_doc(s).model_dump() for s in sessions],
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "has_next_page": skip + len(sessions) < total,
            },
        })
    except AppException as exc:
        return error_response(exc.message, exc.status_code)


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    try:
        session = await session_model.find_session_by_id(session_id)
        if not session or str(session["user_id"]) != str(current_user["_id"]):
            raise NotFoundError("Session")
        return success_response(SessionResponse.from_doc(session).model_dump())
    except AppException as exc:
        return error_response(exc.message, exc.status_code)
