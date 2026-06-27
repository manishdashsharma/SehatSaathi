import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient):
    response = await client.post("/api/v1/documents/upload")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient, auth_headers: dict):
    with patch("app.core.dependencies.get_database") as mock_db:
        mock_col = AsyncMock()
        mock_col.find_one = AsyncMock(
            return_value={
                "_id": "507f1f77bcf86cd799439011",
                "phone": "9876543210",
                "name": "Test",
                "language": "hi",
                "role": "user",
                "consent_given": True,
                "upload_count": 0,
                "call_count": 0,
                "is_active": True,
            }
        )
        mock_db.return_value.users = mock_col

        with patch("app.api.v1.documents.document_service.list_documents") as mock_list:
            mock_list.return_value = {
                "items": [],
                "pagination": {"total": 0, "page": 1, "limit": 20, "has_next_page": False},
            }
            response = await client.get("/api/v1/documents/", headers=auth_headers)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_upload_blocked_after_limit(client: AsyncClient, auth_headers: dict):
    with patch("app.services.user_service.increment_upload_count") as mock_inc:
        from app.core.exceptions import ForbiddenError
        mock_inc.side_effect = ForbiddenError("Upload limit reached")

        import io
        response = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.jpg", io.BytesIO(b"fake"), "image/jpeg")},
            headers=auth_headers,
        )

    assert response.status_code == 403
    assert response.json()["success"] is False
    assert "limit" in response.json()["error"].lower()
