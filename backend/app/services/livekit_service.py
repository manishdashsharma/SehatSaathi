import uuid
from livekit.api import LiveKitAPI, AccessToken, VideoGrants
from app.config import get_settings
import structlog

logger = structlog.get_logger(__name__)


def generate_room_name() -> str:
    return f"session-{uuid.uuid4().hex[:12]}"


async def create_room(room_name: str) -> None:
    settings = get_settings()
    async with LiveKitAPI(
        url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    ) as lk:
        from livekit.api import CreateRoomRequest
        await lk.room.create_room(CreateRoomRequest(name=room_name, empty_timeout=300))
    logger.info("livekit_room_created", room=room_name)


def generate_user_token(room_name: str, participant_identity: str) -> str:
    settings = get_settings()
    token = AccessToken(
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )
    token.with_identity(participant_identity)
    token.with_grants(
        VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        )
    )
    return token.to_jwt()


async def delete_room(room_name: str) -> None:
    settings = get_settings()
    try:
        async with LiveKitAPI(
            url=settings.livekit_url,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        ) as lk:
            from livekit.api import DeleteRoomRequest
            await lk.room.delete_room(DeleteRoomRequest(room=room_name))
        logger.info("livekit_room_deleted", room=room_name)
    except Exception as exc:
        logger.warning("livekit_room_delete_failed", room=room_name, error=str(exc))
