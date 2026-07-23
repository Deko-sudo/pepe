from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

AUTH_ERROR = "Unauthorized."
CSRF_ERROR = "Forbidden."


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest.mark.asyncio
async def test_authenticated_profile_missing_cookie_returns_generic_401(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.json() == {"detail": AUTH_ERROR}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/telegram/session",
        "/api/v1/auth/logout",
        "/api/v1/auth/logout-all",
    ],
)
async def test_session_mutations_require_origin_or_referer(
    client: AsyncClient,
    path: str,
) -> None:
    response = await client.post(path, json={"init_data": "not-used"})

    assert response.status_code == 403
    assert response.json() == {"detail": CSRF_ERROR}


@pytest.mark.asyncio
async def test_legacy_post_me_is_preserved_and_marked_deprecated(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    post_operation = schema["paths"]["/api/v1/users/me"]["post"]

    assert post_operation["deprecated"] is True
    assert "get" in schema["paths"]["/api/v1/users/me"]
