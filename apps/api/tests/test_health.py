from collections.abc import AsyncGenerator, AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
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


@pytest.mark.asyncio
async def test_ready_returns_503_when_postgres_fails(client: AsyncClient) -> None:
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=Exception("connection refused"))

    async def override_db() -> AsyncIterator[AsyncMock]:
        yield mock_session

    app.dependency_overrides[get_db] = override_db
    try:
        response = await client.get("/api/v1/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["dependencies"]["postgres"] == "error"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ready_returns_503_when_redis_fails(client: AsyncClient) -> None:
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()

    async def override_db() -> AsyncIterator[AsyncMock]:
        yield mock_session

    app.dependency_overrides[get_db] = override_db

    mock_redis_instance = AsyncMock()
    mock_redis_instance.ping = AsyncMock(side_effect=Exception("Connection refused"))
    mock_redis_instance.aclose = AsyncMock()

    with patch("redis.asyncio.from_url", return_value=mock_redis_instance):
        try:
            response = await client.get("/api/v1/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "degraded"
            assert data["dependencies"]["redis"] == "error"
        finally:
            app.dependency_overrides.clear()
