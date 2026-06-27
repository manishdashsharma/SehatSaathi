import pytest
import pytest_asyncio
from bson import ObjectId
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from unittest.mock import MagicMock
from app.main import app
import app.database as db_module


@pytest.fixture(autouse=True)
def mock_mongo(monkeypatch):
    mock_client = AsyncMongoMockClient()
    monkeypatch.setattr(db_module, "_mongo_client", mock_client)
    return mock_client


@pytest.fixture(autouse=True)
def mock_minio(monkeypatch):
    mock_client = MagicMock()
    monkeypatch.setattr(db_module, "_minio_client", mock_client)
    monkeypatch.setattr(db_module, "get_minio", lambda: mock_client)
    return mock_client


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
def sample_user():
    return {
        "_id": "507f1f77bcf86cd799439011",
        "phone": "9876543210",
        "name": "Test User",
        "language": "hi",
        "role": "user",
        "consent_given": True,
        "upload_count": 0,
        "call_count": 0,
        "usage_count": 0,
        "is_active": True,
    }


@pytest_asyncio.fixture
async def auth_headers(mock_mongo, sample_user):
    from app.core.security import create_access_token
    from app.config import get_settings

    settings = get_settings()
    db = mock_mongo[settings.mongo_db_name]
    doc = {**sample_user, "_id": ObjectId(sample_user["_id"])}
    await db.users.insert_one(doc)

    token = create_access_token(sample_user["_id"])
    return {"Authorization": f"Bearer {token}"}
