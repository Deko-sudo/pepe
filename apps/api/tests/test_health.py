from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_contains_service_name(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    data = response.json()
    assert data["service"] == "pepe-api"
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_version_returns_pepe(client: AsyncClient) -> None:
    response = await client.get("/api/v1/version")
    data = response.json()
    assert data["name"] == "Pepe"
    assert data["service"] == "pepe-api"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_root_returns_running(client: AsyncClient) -> None:
    response = await client.get("/")
    data = response.json()
    assert data["service"] == "pepe-api"
    assert data["status"] == "running"
