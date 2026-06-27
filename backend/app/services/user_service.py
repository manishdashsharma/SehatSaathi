from app.core.exceptions import ForbiddenError, NotFoundError
from app.models import user as user_model

MAX_UPLOADS = 5
MAX_CALLS = 5


async def get_profile(user_id: str) -> dict:
    user = await user_model.find_user_by_id(user_id)
    if not user:
        raise NotFoundError("User")
    return user


async def update_profile(user_id: str, updates: dict) -> dict:
    user = await user_model.find_user_by_id(user_id)
    if not user:
        raise NotFoundError("User")
    safe_updates = {k: v for k, v in updates.items() if k in ("name", "language")}
    return await user_model.update_user(user_id, safe_updates)


async def update_location(user_id: str, location: dict) -> dict:
    user = await user_model.find_user_by_id(user_id)
    if not user:
        raise NotFoundError("User")
    return await user_model.update_user(user_id, {"location": location})


async def record_consent(user_id: str, given: bool) -> dict:
    if not given:
        raise ForbiddenError("Consent is required to use the platform")
    await user_model.save_consent(user_id)
    return await user_model.find_user_by_id(user_id)


async def increment_upload_count(user_id: str) -> None:
    from app.database import get_database
    from bson import ObjectId
    from datetime import datetime, timezone

    user = await user_model.find_user_by_id(user_id)
    if not user:
        raise NotFoundError("User")

    if user.get("upload_count", 0) >= MAX_UPLOADS:
        raise ForbiddenError(
            f"Upload limit reached. You can upload a maximum of {MAX_UPLOADS} documents."
        )

    db = get_database()
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$inc": {"upload_count": 1},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )


async def increment_call_count(user_id: str) -> None:
    from app.database import get_database
    from bson import ObjectId
    from datetime import datetime, timezone

    user = await user_model.find_user_by_id(user_id)
    if not user:
        raise NotFoundError("User")

    if user.get("call_count", 0) >= MAX_CALLS:
        raise ForbiddenError(
            f"Call limit reached. You can start a maximum of {MAX_CALLS} voice sessions."
        )

    db = get_database()
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$inc": {"call_count": 1},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )


async def list_users(page: int = 1, limit: int = 20, role: str | None = None) -> dict:
    filter_query = {}
    if role:
        filter_query["role"] = role
    skip = (page - 1) * limit
    total, users = await user_model.list_users(filter_query, skip=skip, limit=limit)
    return {
        "items": users,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "has_next_page": skip + len(users) < total,
        },
    }
