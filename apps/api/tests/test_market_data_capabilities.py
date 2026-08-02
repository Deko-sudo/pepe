from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from pepe_quote_core import MarketDataMode

from app.api.dependencies.session import require_current_session
from app.core.config import Settings, settings
from app.core.embedded_chart import EmbeddedChartProvider, canonical_wrapper_origin
from app.core.embedded_chart_security_bundle import compile_security_bundle
from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async def authenticated() -> SimpleNamespace:
        return SimpleNamespace()

    app.dependency_overrides[require_current_session] = authenticated
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as http_client:
            yield http_client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode",
    [MarketDataMode.EMBEDDED, MarketDataMode.LIVE, MarketDataMode.UNAVAILABLE],
)
async def test_unavailable_modes_return_one_versioned_contract(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    mode: MarketDataMode,
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


def test_embedded_chart_defaults_are_disabled_without_a_provider() -> None:
    configured = Settings()

    assert configured.embedded_chart_enabled is False
    assert configured.embedded_chart_provider == "none"


def test_embedded_chart_enabled_without_a_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="embedded_chart_enabled requires"):
        Settings(market_data_mode=MarketDataMode.EMBEDDED, embedded_chart_enabled=True)


@pytest.mark.asyncio
async def test_embedded_mode_capabilities_fail_closed_without_a_provider(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "market_data_mode", MarketDataMode.EMBEDDED)
    monkeypatch.setattr(settings, "embedded_chart_provider", "none")
    monkeypatch.setattr(settings, "embedded_chart_enabled", False)

    response = await client.get("/api/v1/market-data/capabilities")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json() == {
        "contract_version": "v1",
        "mode": "embedded",
        "status": "unavailable",
        "numeric_quotes_available": False,
        "server_candles_available": False,
        "embedded_chart_available": False,
        "embedded_chart_provider": None,
        "embedded_chart_config_version": None,
        "analytics_available": False,
        "quote_cards_visible": False,
        "unavailable_reason_code": "embedded_chart_provider_not_configured",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("slug", ["btc-usdt", "eth-usdt", "xau-usd"])
@pytest.mark.parametrize("timeframe", ["1m", "5m", "15m", "1h", "4h", "1d"])
async def test_embedded_chart_config_validates_canonical_request_but_fails_closed(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    slug: str,
    timeframe: str,
) -> None:
    monkeypatch.setattr(settings, "market_data_mode", MarketDataMode.EMBEDDED)

    response = await client.get(
        f"/api/v1/market-data/embedded-chart-config?slug={slug}&timeframe={timeframe}",
    )

    assert response.status_code == 409
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["reason_code"] == "embedded_chart_provider_not_configured"
    assert "provider" not in response.json()
    assert "iframe_url" not in response.json()


@pytest.mark.asyncio
async def test_embedded_chart_config_rejects_unknown_slug_and_invalid_timeframe(
    client: AsyncClient,
) -> None:
    for query in ("slug=unknown&timeframe=1h", "slug=btc-usdt&timeframe=2h"):
        response = await client.get(f"/api/v1/market-data/embedded-chart-config?{query}")
        assert response.status_code == 422


def test_wrapper_origin_validation_and_settings_matrix() -> None:
    assert (
        canonical_wrapper_origin("http://127.0.0.1:4173/", environment="test")
        == "http://127.0.0.1:4173"
    )
    assert (
        canonical_wrapper_origin("https://WRAPPER.EXAMPLE.TEST:443", environment="test")
        == "https://wrapper.example.test"
    )
    invalid_origins = (
        "http://localhost:4173",
        "http://0.0.0.0:4173",
        "https://wrapper.example.test/path",
        "https://wrapper.example.test?x=1",
        "https://user:pass@wrapper.example.test",
        "https://*.example.test",
        "https://wrapper.example.test\\@evil.test",
        "https://wrapper.example.test/%2fchart",
        "https://2130706433",
        "https://127.1",
        "https://127.0.1",
        "https://017700000001",
        "https://0177.0.0.1",
        "https://0x7f000001",
        "https://0x7f.0.0.1",
    )
    for invalid in invalid_origins:
        with pytest.raises(ValueError):
            canonical_wrapper_origin(invalid, environment="test")
    configured = Settings(
        market_data_mode=MarketDataMode.EMBEDDED,
        embedded_chart_enabled=True,
        embedded_chart_provider=EmbeddedChartProvider.TRADINGVIEW_ISOLATED_WRAPPER,
        embedded_chart_wrapper_origin="http://127.0.0.1:4173",
    )
    assert configured.embedded_chart_wrapper_origin == "http://127.0.0.1:4173"

@pytest.mark.parametrize("environment", ["production", "staging", "preview", "qa", "unknown"])
def test_embedded_chart_provider_is_allowed_only_in_local_environments(environment: str) -> None:
    with pytest.raises(ValueError, match="allowed only in development or test"):
        Settings(
            environment=environment,
            market_data_mode=MarketDataMode.EMBEDDED,
            embedded_chart_enabled=True,
            embedded_chart_provider=EmbeddedChartProvider.TRADINGVIEW_ISOLATED_WRAPPER,
            embedded_chart_wrapper_origin="https://wrapper.example.test",
            session_cookie_secure=True,
            quote_source_label="approved",
            quote_venue_label="approved",
        )


@pytest.mark.asyncio
async def test_w3_wrapper_configuration_matrix(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "environment", "test")
    monkeypatch.setattr(settings, "market_data_mode", MarketDataMode.EMBEDDED)
    monkeypatch.setattr(settings, "embedded_chart_enabled", True)
    monkeypatch.setattr(
        settings, "embedded_chart_provider", EmbeddedChartProvider.TRADINGVIEW_ISOLATED_WRAPPER,
    )
    monkeypatch.setattr(settings, "embedded_chart_wrapper_origin", "http://127.0.0.1:4173")
    compile_security_bundle(
        {
            "version": 1,
            "environment": "test",
            "market_data_mode": "embedded",
            "embedded_chart_enabled": True,
            "embedded_chart_provider": "tradingview_isolated_wrapper",
            "embedded_chart_kill_switch": False,
            "parent_origin": "http://127.0.0.1:4174",
            "wrapper_origin": "http://127.0.0.1:4173",
        },
        tmp_path / "bundle",
    )
    monkeypatch.setattr(settings, "embedded_chart_security_bundle_path", str(tmp_path / "bundle"))
    for slug in ("btc-usdt", "eth-usdt", "xau-usd"):
        for timeframe in ("1m", "5m", "15m", "1h", "4h", "1d"):
            response = await client.get(
                f"/api/v1/market-data/embedded-chart-config?slug={slug}&timeframe={timeframe}",
            )
            assert response.status_code == 200
            assert response.headers["cache-control"] == "private, no-store"
            assert (
                response.json()["wrapper_url"] == f"http://127.0.0.1:4173/chart/{slug}/{timeframe}"
            )
            assert "?" not in response.json()["wrapper_url"]
            assert "BINANCE:" not in response.json()["wrapper_url"]


@pytest.mark.asyncio
async def test_killed_bundle_withdraws_embedded_chart_without_leaking_origins(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    compile_security_bundle(
        {
            "version": 1,
            "environment": "test",
            "market_data_mode": "embedded",
            "embedded_chart_enabled": True,
            "embedded_chart_provider": "tradingview_isolated_wrapper",
            "embedded_chart_kill_switch": True,
            "parent_origin": "http://127.0.0.1:4180",
            "wrapper_origin": "http://127.0.0.1:4182",
        },
        tmp_path / "bundle",
    )
    monkeypatch.setattr(settings, "embedded_chart_security_bundle_path", str(tmp_path / "bundle"))

    capabilities = await client.get("/api/v1/market-data/capabilities")
    configuration = await client.get(
        "/api/v1/market-data/embedded-chart-config?slug=btc-usdt&timeframe=1h",
    )

    assert capabilities.status_code == 200
    assert capabilities.headers["cache-control"] == "private, no-store"
    assert capabilities.json()["embedded_chart_available"] is False
    assert capabilities.json()["embedded_chart_provider"] is None
    assert configuration.status_code == 409
    assert configuration.headers["cache-control"] == "private, no-store"
    assert "127.0.0.1:4182" not in configuration.text
    assert "tradingview" not in configuration.text.lower()


@pytest.mark.asyncio
async def test_bundle_from_another_runtime_environment_is_unavailable(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    compile_security_bundle(
        {
            "version": 1,
            "environment": "development",
            "market_data_mode": "embedded",
            "embedded_chart_enabled": True,
            "embedded_chart_provider": "tradingview_isolated_wrapper",
            "embedded_chart_kill_switch": False,
            "parent_origin": "http://localhost:4000",
            "wrapper_origin": "http://127.0.0.1:4173",
        },
        tmp_path / "bundle",
    )
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "market_data_mode", MarketDataMode.EMBEDDED)
    monkeypatch.setattr(settings, "embedded_chart_enabled", True)
    monkeypatch.setattr(
        settings,
        "embedded_chart_provider",
        EmbeddedChartProvider.TRADINGVIEW_ISOLATED_WRAPPER,
    )
    monkeypatch.setattr(
        settings,
        "embedded_chart_wrapper_origin",
        "http://127.0.0.1:4173",
    )
    monkeypatch.setattr(settings, "embedded_chart_security_bundle_path", str(tmp_path / "bundle"))

    capabilities = await client.get("/api/v1/market-data/capabilities")
    configuration = await client.get(
        "/api/v1/market-data/embedded-chart-config?slug=btc-usdt&timeframe=1h",
    )

    assert capabilities.json()["embedded_chart_available"] is False
    assert configuration.status_code == 409
    assert "127.0.0.1:4173" not in configuration.text
