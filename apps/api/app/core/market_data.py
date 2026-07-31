import json
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlencode

from pepe_quote_core import MarketDataMode, has_machine_readable_market_data
from pydantic import BaseModel

CONTRACT_VERSION: Literal["v1"] = "v1"
EMBEDDED_CHART_PROVIDER_NONE = "none"
EMBEDDED_CHART_PROVIDER_TRADINGVIEW = "tradingview"
EmbeddedChartProvider = Literal["none", "tradingview"]


@dataclass(frozen=True)
class EmbeddedDisplayMapping:
    canonical_slug: str
    provider_symbol: str
    source_label: str
    display_name: str
    asset_class: str
    market_semantics: str
    fallback_url: str


_EMBEDDED_DISPLAY_MAPPINGS: dict[str, EmbeddedDisplayMapping] = {
    "btc-usdt": EmbeddedDisplayMapping(
        "btc-usdt",
        "BINANCE:BTCUSDT",
        "Binance spot",
        "BTC / USDT",
        "crypto_spot",
        "Exchange-specific BTC/USDT spot market",
        "https://www.tradingview.com/symbols/BTCUSDT/?exchange=BINANCE",
    ),
    "eth-usdt": EmbeddedDisplayMapping(
        "eth-usdt",
        "BINANCE:ETHUSDT",
        "Binance spot",
        "ETH / USDT",
        "crypto_spot",
        "Exchange-specific ETH/USDT spot market",
        "https://www.tradingview.com/symbols/ETHUSDT/?exchange=BINANCE",
    ),
    "xau-usd": EmbeddedDisplayMapping(
        "xau-usd",
        "OANDA:XAUUSD",
        "OANDA spot reference",
        "XAU / USD",
        "metal_fx_spot",
        "Gold spot / U.S. Dollar reference quoted by OANDA",
        "https://www.tradingview.com/symbols/XAUUSD/",
    ),
}
_ALLOWED_INTERVALS: dict[str, str] = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "1h": "60",
    "4h": "240",
    "1d": "D",
}


class MarketDataCapabilityResponse(BaseModel):
    contract_version: Literal["v1"] = CONTRACT_VERSION
    mode: MarketDataMode
    status: Literal["available", "unavailable"]
    numeric_quotes_available: bool
    server_candles_available: bool
    embedded_chart_available: bool = False
    analytics_available: bool = False
    quote_cards_visible: bool
    unavailable_reason_code: str | None = None


class EmbeddedChartConfigResponse(BaseModel):
    contract_version: Literal["v1"] = CONTRACT_VERSION
    provider: Literal["tradingview"]
    canonical_slug: str
    provider_symbol: str
    interval: str
    source_label: str
    display_name: str
    market_semantics: str
    delay_disclosure: str
    iframe_url: str
    fallback_url: str
    attribution: str


def embedded_chart_available(
    mode: MarketDataMode, provider: EmbeddedChartProvider, enabled: bool,
) -> bool:
    return (
        mode is MarketDataMode.EMBEDDED
        and provider == EMBEDDED_CHART_PROVIDER_TRADINGVIEW
        and enabled
    )


def capabilities_for(
    mode: MarketDataMode, *, provider: EmbeddedChartProvider = "none", enabled: bool = False,
) -> MarketDataCapabilityResponse:
    machine_readable = has_machine_readable_market_data(mode)
    chart_available = embedded_chart_available(mode, provider, enabled)
    return MarketDataCapabilityResponse(
        mode=mode,
        status="available" if machine_readable or chart_available else "unavailable",
        numeric_quotes_available=machine_readable,
        server_candles_available=machine_readable,
        embedded_chart_available=chart_available,
        quote_cards_visible=machine_readable,
        unavailable_reason_code=None
        if machine_readable or chart_available
        else "market_data_not_configured",
    )


def embedded_chart_config(slug: str, timeframe: str) -> EmbeddedChartConfigResponse | None:
    mapping = _EMBEDDED_DISPLAY_MAPPINGS.get(slug)
    interval = _ALLOWED_INTERVALS.get(timeframe)
    if mapping is None or interval is None:
        return None
    widget_config = {
        "autosize": True,
        "backgroundColor": "#0f0f0f",
        "gridColor": "rgba(242, 242, 242, 0.06)",
        "hide_side_toolbar": True,
        "hide_top_toolbar": False,
        "interval": interval,
        "locale": "en",
        "symbol": mapping.provider_symbol,
        "theme": "dark",
        "timezone": "Etc/UTC",
    }
    iframe_url = (
        "https://www.tradingview-widget.com/embed-widget/advanced-chart/?"
        + urlencode({"locale": "en"})
        + "#"
        + urlencode({"config": json.dumps(widget_config, separators=(",", ":"))})
    )
    return EmbeddedChartConfigResponse(
        provider="tradingview",
        canonical_slug=mapping.canonical_slug,
        provider_symbol=mapping.provider_symbol,
        interval=timeframe,
        source_label=mapping.source_label,
        display_name=mapping.display_name,
        market_semantics=mapping.market_semantics,
        delay_disclosure="Delay status is provided by TradingView and may vary by venue.",
        iframe_url=iframe_url,
        fallback_url=mapping.fallback_url,
        attribution=(
            "Chart data and branding are provided by TradingView; Pepe does not store the "
            "displayed raw market data."
        ),
    )


def unavailable_market_data_error(mode: MarketDataMode, capability: str) -> dict[str, str]:
    return {
        "contract_version": CONTRACT_VERSION,
        "code": "market_data_unavailable",
        "capability": capability,
        "mode": mode.value,
        "reason_code": "market_data_not_configured",
        "message": "Machine-readable market data is unavailable in the current mode.",
    }
