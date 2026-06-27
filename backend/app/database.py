import boto3
from botocore.client import Config
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from app.config import get_settings

_mongo_client: AsyncIOMotorClient | None = None
_minio_client = None


def get_database() -> AsyncIOMotorDatabase:
    settings = get_settings()
    return _mongo_client[settings.mongo_db_name]


def get_minio():
    return _minio_client


async def connect_mongo() -> None:
    global _mongo_client
    settings = get_settings()
    _mongo_client = AsyncIOMotorClient(settings.mongo_uri)
    await _create_indexes(get_database())


async def disconnect_mongo() -> None:
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None


def connect_minio() -> None:
    global _minio_client
    settings = get_settings()
    _minio_client = boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    _ensure_bucket()


def _ensure_bucket() -> None:
    settings = get_settings()
    try:
        _minio_client.head_bucket(Bucket=settings.minio_bucket)
    except Exception:
        _minio_client.create_bucket(Bucket=settings.minio_bucket)


async def _create_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.users.create_index([("phone", ASCENDING)], unique=True)
    await db.users.create_index([("role", ASCENDING), ("is_active", ASCENDING)])

    await db.documents.create_index([("user_id", ASCENDING), ("is_active", ASCENDING)])
    await db.documents.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    await db.documents.create_index([("status", ASCENDING)])

    await db.sessions.create_index([("user_id", ASCENDING), ("is_active", ASCENDING)])
    await db.sessions.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    await db.sessions.create_index(
        [("livekit_room", ASCENDING)], unique=True, sparse=True
    )

    await db.agent_verdicts.create_index(
        [("document_id", ASCENDING), ("agent_type", ASCENDING)]
    )
    await db.agent_verdicts.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    await db.agent_verdicts.create_index([("session_id", ASCENDING)])

    await db.emergency_contacts.create_index(
        [("user_id", ASCENDING), ("is_active", ASCENDING)]
    )

    await db.refresh_tokens.create_index([("user_id", ASCENDING)])
    await db.refresh_tokens.create_index([("token", ASCENDING)], unique=True)
    await db.refresh_tokens.create_index(
        [("expires_at", ASCENDING)], expireAfterSeconds=0
    )

    await db.audit_logs.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    await db.consent_records.create_index([("user_id", ASCENDING)], unique=True)
