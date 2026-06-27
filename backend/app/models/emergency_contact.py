from datetime import datetime, timezone
from bson import ObjectId
from app.database import get_database


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    if "user_id" in doc and isinstance(doc["user_id"], ObjectId):
        doc["user_id"] = str(doc["user_id"])
    return doc


async def create_contact(data: dict) -> dict:
    db = get_database()
    now = datetime.now(timezone.utc)
    doc = {**data, "is_active": True, "created_at": now, "updated_at": now}
    result = await db.emergency_contacts.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


async def find_contacts_by_user(user_id: str) -> list[dict]:
    db = get_database()
    docs = await db.emergency_contacts.find(
        {"user_id": user_id, "is_active": True}
    ).to_list(length=10)
    return [_serialize(d) for d in docs]


async def deactivate_contact(contact_id: str) -> None:
    db = get_database()
    await db.emergency_contacts.update_one(
        {"_id": ObjectId(contact_id)},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
    )
