from typing import Literal

from pepe_quote_core import MarketDataMode, has_machine_readable_market_data
from pydantic import BaseModel

from app.core.embedded_chart import EmbeddedChartProvider

CONTRACT_VERSION: Literal["v1"] = "v1"


class MarketDataCapabilityResponse(BaseModel):
    contract_version: Literal["v1"] = CONTRACT_VERSION
    mode: MarketDataMode
    status: Literal["available", "unavailable"]
    numeric_quotes_available: bool
    server_candles_available: bool
    embedded_chart_available: bool = False
    embedded_chart_provider: EmbeddedChartProvider | None = None
    embedded_chart_config_version: Literal[1] | None = None
    analytics_available: bool = False
    quote_cards_visible: bool
    unavailable_reason_code: str | None = None


def capabilities_for(
    mode: MarketDataMode,
    *,
    provider: EmbeddedChartProvider = EmbeddedChartProvider.NONE,
    enabled: bool = False,
) -> MarketDataCapabilityResponse:
    machine_readable = has_machine_readable_market_data(mode)
    embedded_available = enabled and provider is EmbeddedChartProvider.TRADINGVIEW_ISOLATED_WRAPPER
    embedded_reason = (
        "embedded_chart_provider_not_configured"
        if mode is MarketDataMode.EMBEDDED and not embedded_available
        else "market_data_not_configured"
    )
    return MarketDataCapabilityResponse(
        mode=mode,
        status="available" if machine_readable else "unavailable",
        numeric_quotes_available=machine_readable,
        server_candles_available=machine_readable,
        embedded_chart_available=embedded_available,
        embedded_chart_provider=provider if embedded_available else None,
        embedded_chart_config_version=1 if embedded_available else None,
        analytics_available=False,
        quote_cards_visible=machine_readable,
        unavailable_reason_code=None if machine_readable else embedded_reason,
    )


def unavailable_market_data_error(
    mode: MarketDataMode,
    capability: str,
    *,
    reason_code: str = "market_data_not_configured",
) -> dict[str, str]:
    return {
        "contract_version": CONTRACT_VERSION,
        "code": "market_data_unavailable",
        "capability": capability,
        "mode": mode.value,
        "reason_code": reason_code,
        "message": "Machine-readable market data is unavailable in the current mode.",
    }
