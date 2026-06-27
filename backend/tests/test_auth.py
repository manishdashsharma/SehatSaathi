import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_new_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"phone": "9876543210", "name": "Ramesh Kumar", "language": "hi"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["user"]["phone"] == "9876543210"


@pytest.mark.asyncio
async def test_register_existing_user_returns_tokens(client: AsyncClient):
    payload = {"phone": "9876543210", "name": "Ramesh Kumar", "language": "hi"}
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_register_invalid_phone(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"phone": "123", "name": "Test", "language": "hi"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert response.status_code == 401
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_logout_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "any"},
    )
    assert response.status_code == 401
