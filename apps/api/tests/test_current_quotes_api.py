from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.session import require_current_session
from app.core.config import settings
from app.main import app
from app.modules.market_data.quotes import CurrentQuoteResolution


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


@pytest.mark.asyncio
async def test_current_quote_batch_distinguishes_unknown_from_unavailable_and_closes_once(
    client: AsyncClient,
) -> None:
    from app.api.v1 import quotes

    created: list[FakeQuoteService] = []

    class FakeQuoteService:
        def __init__(self) -> None:
            self.closed = False
            created.append(self)

        async def resolve_current_quote_by_slug(
            self,
            db: object,
            slug: str,
        ) -> CurrentQuoteResolution:
            del db
            return CurrentQuoteResolution(quote=None, not_found=slug == "missing")

        async def close(self) -> None:
            self.closed = True

    with patch.object(quotes, "CurrentQuoteService", FakeQuoteService):
        response = await client.get("/api/v1/assets/quotes?slug=unavailable&slug=missing")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "unavailable": ["unavailable"],
        "not_found": ["missing"],
    }
    assert response.headers["cache-control"] == "private, no-store"
    assert len(created) == 1
    assert created[0].closed is True


@pytest.mark.asyncio
async def test_current_quote_batch_uses_configured_unique_slug_limit(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "quote_api_batch_limit", 1)

    response = await client.get("/api/v1/assets/quotes?slug=btc-usdt&slug=eth-usdt&slug=btc-usdt")

    assert response.status_code == 422
    assert response.json() == {"detail": "At most 1 unique slugs may be requested"}
    assert response.headers["cache-control"] == "private, no-store"
