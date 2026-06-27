import asyncio
from datetime import datetime, timezone
from bson import ObjectId
from app.database import get_database


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


async def create_user(data: dict) -> dict:
    db = get_database()
    now = datetime.now(timezone.utc)
    doc = {**data, "is_active": True, "created_at": now, "updated_at": now}
    result = await db.users.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


async def find_user_by_phone(phone: str) -> dict | None:
    db = get_database()
    user = await db.users.find_one({"phone": phone, "is_active": True})
    return _serialize(user) if user else None


async def find_user_by_id(user_id: str) -> dict | None:
    db = get_database()
    user = await db.users.find_one({"_id": ObjectId(user_id), "is_active": True})
    return _serialize(user) if user else None


async def update_user(user_id: str, data: dict) -> dict | None:
    db = get_database()
    data["updated_at"] = datetime.now(timezone.utc)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": data})
    return await find_user_by_id(user_id)


async def list_users(
    filter: dict, skip: int = 0, limit: int = 20
) -> tuple[int, list[dict]]:
    db = get_database()
    query = {**filter, "is_active": True}
    total, users = await asyncio.gather(
        db.users.count_documents(query),
        db.users.find(query, {"password": 0})
        .skip(skip)
        .limit(limit)
        .to_list(length=limit),
    )
    return total, [_serialize(u) for u in users]


async def deactivate_user(user_id: str) -> None:
    db = get_database()
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
    )


async def save_consent(user_id: str) -> None:
    db = get_database()
    now = datetime.now(timezone.utc)
    await asyncio.gather(
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"consent_given": True, "consent_at": now, "updated_at": now}},
        ),
        db.consent_records.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "given_at": now}},
            upsert=True,
        ),
    )
