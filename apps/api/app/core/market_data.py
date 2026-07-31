from typing import Literal

from pepe_quote_core import MarketDataMode, has_machine_readable_market_data
from pydantic import BaseModel

CONTRACT_VERSION: Literal["v1"] = "v1"


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


def capabilities_for(mode: MarketDataMode) -> MarketDataCapabilityResponse:
    available = has_machine_readable_market_data(mode)
    return MarketDataCapabilityResponse(
        mode=mode,
        status="available" if available else "unavailable",
        numeric_quotes_available=available,
        server_candles_available=available,
        quote_cards_visible=available,
        unavailable_reason_code=None if available else "market_data_not_configured",
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
