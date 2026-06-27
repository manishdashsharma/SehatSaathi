from datetime import datetime, timezone
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    refresh_token_expires_at,
)
from app.core.exceptions import UnauthorizedError
from app.database import get_database
from app.models import user as user_model


async def register_or_login(phone: str, name: str, language: str) -> dict:
    existing = await user_model.find_user_by_phone(phone)
    if existing:
        return await _issue_tokens(existing)

    new_user = await user_model.create_user({
        "phone": phone,
        "name": name,
        "language": language,
        "role": "user",
        "consent_given": False,
        "upload_count": 0,
        "call_count": 0,
        "location": None,
    })
    return await _issue_tokens(new_user)


async def refresh_access_token(refresh_token: str) -> dict:
    try:
        payload = decode_refresh_token(refresh_token)
    except ValueError as exc:
        raise UnauthorizedError(str(exc))

    user_id = payload.get("sub")
    db = get_database()

    stored = await db.refresh_tokens.find_one({"token": refresh_token, "user_id": user_id})
    if not stored:
        raise UnauthorizedError("Refresh token not found or revoked")

    user = await user_model.find_user_by_id(user_id)
    if not user:
        raise UnauthorizedError("User not found")

    await db.refresh_tokens.delete_one({"_id": stored["_id"]})
    return await _issue_tokens(user)


async def revoke_refresh_token(user_id: str, refresh_token: str) -> None:
    db = get_database()
    await db.refresh_tokens.delete_one({"token": refresh_token, "user_id": user_id})


async def _issue_tokens(user: dict) -> dict:
    db = get_database()
    user_id = str(user["_id"])

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    await db.refresh_tokens.insert_one({
        "user_id": user_id,
        "token": refresh_token,
        "expires_at": refresh_token_expires_at(),
        "created_at": datetime.now(timezone.utc),
    })

    return {"access_token": access_token, "refresh_token": refresh_token, "user": user}
