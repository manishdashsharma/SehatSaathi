import asyncio
from datetime import datetime, timezone
from bson import ObjectId
from app.database import get_database


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    for field in ("user_id", "document_id", "session_id"):
        if field in doc and isinstance(doc[field], ObjectId):
            doc[field] = str(doc[field])
    return doc


async def create_verdict(data: dict) -> dict:
    db = get_database()
    now = datetime.now(timezone.utc)
    doc = {**data, "is_active": True, "created_at": now, "updated_at": now}
    result = await db.agent_verdicts.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


async def find_verdicts_by_document(document_id: str) -> list[dict]:
    db = get_database()
    docs = await db.agent_verdicts.find(
        {"document_id": document_id, "is_active": True}
    ).to_list(length=10)
    return [_serialize(d) for d in docs]


async def find_verdicts_by_session(session_id: str) -> list[dict]:
    db = get_database()
    docs = await db.agent_verdicts.find(
        {"session_id": session_id, "is_active": True}
    ).to_list(length=10)
    return [_serialize(d) for d in docs]


async def bulk_create_verdicts(verdicts: list[dict]) -> list[dict]:
    db = get_database()
    now = datetime.now(timezone.utc)
    docs = [{**v, "is_active": True, "created_at": now, "updated_at": now} for v in verdicts]
    result = await db.agent_verdicts.insert_many(docs)
    for doc, inserted_id in zip(docs, result.inserted_ids):
        doc["_id"] = str(inserted_id)
    return [_serialize(d) for d in docs]
