import asyncio
from datetime import datetime, timezone
from bson import ObjectId
from app.database import get_database


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    if "user_id" in doc and isinstance(doc["user_id"], ObjectId):
        doc["user_id"] = str(doc["user_id"])
    return doc


async def create_document(data: dict) -> dict:
    db = get_database()
    now = datetime.now(timezone.utc)
    doc = {**data, "is_active": True, "created_at": now, "updated_at": now}
    result = await db.documents.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


async def find_document_by_id(document_id: str) -> dict | None:
    db = get_database()
    doc = await db.documents.find_one(
        {"_id": ObjectId(document_id), "is_active": True}
    )
    return _serialize(doc) if doc else None


async def list_documents(
    user_id: str, skip: int = 0, limit: int = 20
) -> tuple[int, list[dict]]:
    db = get_database()
    query = {"user_id": user_id, "is_active": True}
    total, docs = await asyncio.gather(
        db.documents.count_documents(query),
        db.documents.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit),
    )
    return total, [_serialize(d) for d in docs]


async def update_document(document_id: str, data: dict) -> dict | None:
    db = get_database()
    data["updated_at"] = datetime.now(timezone.utc)
    await db.documents.update_one({"_id": ObjectId(document_id)}, {"$set": data})
    return await find_document_by_id(document_id)


async def deactivate_document(document_id: str) -> None:
    db = get_database()
    await db.documents.update_one(
        {"_id": ObjectId(document_id)},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
    )
