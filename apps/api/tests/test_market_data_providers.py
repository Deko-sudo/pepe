from __future__ import annotations

import uuid

import pytest

from app.modules.market_data.errors import (
    InstrumentNotMapped,
    ProviderAuthenticationFailure,
    ProviderRateLimited,
    ProviderUnavailable,
)
from app.modules.market_data.providers import (
    ProviderCapabilities,
    ProviderHealth,
    ProviderMapping,
    select_mapping,
)


def test_provider_error_taxonomy_exposes_only_safe_retry_metadata() -> None:
    unavailable = ProviderUnavailable()
    limited = ProviderRateLimited(retry_after_seconds=30)
    auth_failure = ProviderAuthenticationFailure()

    assert unavailable.code == "provider_unavailable"
    assert unavailable.retryable is True
    assert unavailable.public_message == "Market data provider is temporarily unavailable."
    assert limited.retry_after_seconds == 30
    assert auth_failure.retryable is False
    assert "secret" not in str(auth_failure).lower()


def test_provider_capabilities_only_declare_future_quote_and_candle_support() -> None:
    capabilities = ProviderCapabilities(
        supports_mapping_discovery=True,
        supports_availability_checks=True,
        supports_quotes=False,
        supports_candles=False,
        rate_limit_metadata_available=False,
    )

    assert capabilities.supports_quotes is False
    assert capabilities.supports_candles is False


def test_enabled_mapping_selection_is_priority_then_provider_key() -> None:
    instrument_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    selected = select_mapping(
        instrument_id,
        [
            ProviderMapping(instrument_id, "zeta", "BTCUSDT", "spot", 2, True),
            ProviderMapping(instrument_id, "alpha", "BTC-USDT", "spot", 1, True),
            ProviderMapping(instrument_id, "disabled", "BTC", "spot", 0, False),
        ],
    )

    assert selected.provider_key == "alpha"
    assert selected.provider_symbol == "BTC-USDT"


def test_mapping_selection_ignores_enabled_mappings_for_other_instruments() -> None:
    instrument_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    other_instrument_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    selected = select_mapping(
        instrument_id,
        [
            ProviderMapping(other_instrument_id, "alpha", "ETH-USDT", "spot", 1, True),
            ProviderMapping(instrument_id, "zeta", "BTC-USDT", "spot", 2, True),
        ],
    )

    assert selected.instrument_id == instrument_id
    assert selected.provider_key == "zeta"


def test_mapping_selection_normalizes_absence_to_domain_error() -> None:
    with pytest.raises(InstrumentNotMapped):
        select_mapping(uuid.uuid4(), [])


def test_provider_health_contract_is_immutable() -> None:
    health = ProviderHealth(is_available=True, checked_at=None, detail=None)

    with pytest.raises(AttributeError):
        health.is_available = False  # type: ignore[misc]
