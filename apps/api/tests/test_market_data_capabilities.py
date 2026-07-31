from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from pepe_quote_core import MarketDataMode

from app.api.dependencies.session import require_current_session
from app.core.config import settings
from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async def authenticated() -> SimpleNamespace:
        return SimpleNamespace()

    app.dependency_overrides[require_current_session] = authenticated
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test",
        ) as http_client:
            yield http_client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode", [MarketDataMode.EMBEDDED, MarketDataMode.LIVE, MarketDataMode.UNAVAILABLE],
)
async def test_unavailable_modes_return_one_versioned_contract(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, mode: MarketDataMode,
) -> None:
    monkeypatch.setattr(settings, "market_data_mode", mode)
    quote = await client.get("/api/v1/assets/quotes?slug=btc-usdt")
    candles = await client.get("/api/v1/market-data/instruments/btc-usdt/candles?timeframe=1m")
    for response, capability in ((quote, "quotes"), (candles, "candles")):
        assert response.status_code == 409
        assert response.headers["cache-control"] == "private, no-store"
        assert response.json() == {
            "contract_version": "v1",
            "code": "market_data_unavailable",
            "capability": capability,
            "mode": mode.value,
            "reason_code": "market_data_not_configured",
            "message": "Machine-readable market data is unavailable in the current mode.",
        }


@pytest.mark.asyncio
async def test_capabilities_are_authenticated_and_private_no_store(client: AsyncClient) -> None:
    response = await client.get("/api/v1/market-data/capabilities")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["contract_version"] == "v1"
    assert response.json()["mode"] == "demo"
    assert response.json()["numeric_quotes_available"] is True
