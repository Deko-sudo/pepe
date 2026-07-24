from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.session import require_current_session
from app.db.models.asset_instrument import AssetInstrument
from app.main import app


def make_asset(slug: str = "btc-usdt", *, enabled: bool = True) -> AssetInstrument:
    return AssetInstrument(
        id=uuid.UUID("a6d8c260-3f98-4d19-9e87-8dd33413b401"),
        slug=slug,
        symbol="BTC/USDT",
        display_name="Bitcoin / Tether",
        asset_class="crypto_spot",
        market_type="spot",
        base_asset="BTC",
        quote_asset="USDT",
        price_precision=2,
        quantity_precision=8,
        timezone="UTC",
        calendar_kind="always_open",
        trading_calendar="crypto-24x7",
        is_enabled=enabled,
        metadata_version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


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
async def test_asset_list_requires_a_session() -> None:
    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/assets")

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized."}


@pytest.mark.asyncio
async def test_asset_list_returns_only_canonical_metadata_and_next_cursor(
    client: AsyncClient,
) -> None:
    from app.api.v1 import assets

    with patch.object(
        assets,
        "list_enabled_instruments",
        AsyncMock(return_value=([make_asset()], "eth-usdt")),
    ):
        response = await client.get("/api/v1/assets")

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_cursor"] == "eth-usdt"
    assert payload["items"][0]["slug"] == "btc-usdt"
    assert {
        "provider_key",
        "provider_symbol",
        "price",
        "volume",
        "candles",
        "analytics",
    }.isdisjoint(
        payload["items"][0],
    )


@pytest.mark.asyncio
async def test_asset_detail_treats_disabled_or_unknown_asset_as_not_found(
    client: AsyncClient,
) -> None:
    from app.api.v1 import assets

    with patch.object(assets, "get_enabled_instrument_by_slug", AsyncMock(return_value=None)):
        response = await client.get("/api/v1/assets/disabled-asset")

    assert response.status_code == 404
    assert response.json() == {"detail": "Asset not found"}


@pytest.mark.asyncio
async def test_asset_list_passes_keyset_cursor_and_controlled_filter(client: AsyncClient) -> None:
    from app.api.v1 import assets

    list_assets = AsyncMock(return_value=([], None))
    with patch.object(assets, "list_enabled_instruments", list_assets):
        response = await client.get("/api/v1/assets?limit=2&after=btc-usdt&asset_class=crypto_spot")

    assert response.status_code == 200
    assert list_assets.await_args is not None
    assert list_assets.await_args.kwargs == {
        "after": "btc-usdt",
        "asset_class": "crypto_spot",
        "limit": 2,
    }
