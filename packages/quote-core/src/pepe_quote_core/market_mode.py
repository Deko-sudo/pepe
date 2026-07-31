from enum import StrEnum


class MarketDataMode(StrEnum):
    """Deployment-wide market-data capability mode."""

    DEMO = "demo"
    EMBEDDED = "embedded"
    LIVE = "live"
    UNAVAILABLE = "unavailable"


MACHINE_READABLE_DATA_MODES = frozenset({MarketDataMode.DEMO})


def has_machine_readable_market_data(mode: MarketDataMode) -> bool:
    return mode in MACHINE_READABLE_DATA_MODES


def validate_market_data_policy(
    *,
    environment: str,
    mode: MarketDataMode,
    quote_fake_provider_enabled: bool,
    candle_fake_provider_enabled: bool,
) -> None:
    """Reject effective configurations that could expose synthetic data outside demo."""
    normalized_environment = environment.strip().lower()
    if normalized_environment == "production" and mode is MarketDataMode.DEMO:
        raise ValueError("market_data_mode=demo is forbidden in production")
    if mode is not MarketDataMode.DEMO and quote_fake_provider_enabled:
        raise ValueError("quote_fake_provider_enabled is allowed only in market_data_mode=demo")
    if mode is not MarketDataMode.DEMO and candle_fake_provider_enabled:
        raise ValueError("candle_fake_provider_enabled is allowed only in market_data_mode=demo")
