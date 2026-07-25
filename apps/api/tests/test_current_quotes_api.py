from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.session import require_current_session
from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async def authenticated() -> SimpleNamespace:
        return SimpleNamespace()

    app.dependency_overrides[require_current_session] = authenticated
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_current_quote_returns_safe_unavailable_response_without_durable_quote(
    client: AsyncClient,
) -> None:
    from app.api.v1 import quotes

    with patch.object(quotes, "get_current_quote_by_slug", AsyncMock(return_value=None)):
        response = await client.get("/api/v1/assets/btc-usdt/quote")

    assert response.status_code == 503
    assert response.json() == {"detail": "Current quote is unavailable"}
    assert response.headers["cache-control"] == "private, no-store"
