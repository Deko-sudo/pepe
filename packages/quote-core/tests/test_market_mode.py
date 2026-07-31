import pytest

from pepe_quote_core import MarketDataMode, validate_market_data_policy


@pytest.mark.parametrize("mode", ["demo", "embedded", "live", "unavailable"])
def test_market_data_mode_accepts_only_supported_values(mode: str) -> None:
    assert MarketDataMode(mode).value == mode


def test_market_data_mode_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        MarketDataMode("provider")


@pytest.mark.parametrize(
    ("environment", "mode", "quote_fake", "candle_fake"),
    [
        ("production", "demo", False, False),
        ("development", "embedded", True, False),
        ("development", "embedded", False, True),
        ("development", "live", True, False),
        ("development", "unavailable", False, True),
    ],
)
def test_market_data_policy_rejects_unsafe_effective_configuration(
    environment: str,
    mode: str,
    quote_fake: bool,
    candle_fake: bool,
) -> None:
    with pytest.raises(ValueError):
        validate_market_data_policy(
            environment=environment,
            mode=MarketDataMode(mode),
            quote_fake_provider_enabled=quote_fake,
            candle_fake_provider_enabled=candle_fake,
        )


def test_demo_remains_available_for_development() -> None:
    validate_market_data_policy(
        environment="development",
        mode=MarketDataMode.DEMO,
        quote_fake_provider_enabled=True,
        candle_fake_provider_enabled=True,
    )
