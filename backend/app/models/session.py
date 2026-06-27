import asyncio
from datetime import datetime, timezone
from bson import ObjectId
from app.database import get_database


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    for field in ("user_id", "document_id"):
        if field in doc and isinstance(doc[field], ObjectId):
            doc[field] = str(doc[field])
    return doc


async def create_session(data: dict) -> dict:
    db = get_database()
    now = datetime.now(timezone.utc)
    doc = {
        **data,
        "status": "active",
        "emergency_flagged": False,
        "is_active": True,
        "started_at": now,
        "ended_at": None,
        "transcript": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.sessions.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


async def find_session_by_id(session_id: str) -> dict | None:
    db = get_database()
    doc = await db.sessions.find_one({"_id": ObjectId(session_id), "is_active": True})
    return _serialize(doc) if doc else None


async def find_session_by_room(livekit_room: str) -> dict | None:
    db = get_database()
    doc = await db.sessions.find_one({"livekit_room": livekit_room, "is_active": True})
    return _serialize(doc) if doc else None


async def list_sessions(
    user_id: str, skip: int = 0, limit: int = 20
) -> tuple[int, list[dict]]:
    db = get_database()
    query = {"user_id": user_id, "is_active": True}
    total, docs = await asyncio.gather(
        db.sessions.count_documents(query),
        db.sessions.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit),
    )
    return total, [_serialize(d) for d in docs]


async def update_session(session_id: str, data: dict) -> dict | None:
    db = get_database()
    data["updated_at"] = datetime.now(timezone.utc)
    await db.sessions.update_one({"_id": ObjectId(session_id)}, {"$set": data})
    return await find_session_by_id(session_id)


async def end_session(session_id: str, transcript: str | None = None) -> dict | None:
    db = get_database()
    now = datetime.now(timezone.utc)
    update_data = {
        "status": "completed",
        "ended_at": now,
        "updated_at": now,
    }
    if transcript is not None:
        update_data["transcript"] = transcript
    await db.sessions.update_one({"_id": ObjectId(session_id)}, {"$set": update_data})
    return await find_session_by_id(session_id)


async def flag_emergency(session_id: str) -> None:
    db = get_database()
    await db.sessions.update_one(
        {"_id": ObjectId(session_id)},
        {
            "$set": {
                "emergency_flagged": True,
                "status": "flagged",
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
