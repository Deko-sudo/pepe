from __future__ import annotations

import uuid

import pytest

from app.modules.market_data.domain import (
    AssetClass,
    CalendarKind,
    CanonicalInstrument,
    MarketType,
)


def make_instrument(**overrides: object) -> CanonicalInstrument:
    values: dict[str, object] = {
        "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "slug": "btc-usdt",
        "symbol": "BTC/USDT",
        "display_name": "Bitcoin / Tether",
        "asset_class": AssetClass.CRYPTO_SPOT,
        "market_type": MarketType.SPOT,
        "base_asset": "BTC",
        "quote_asset": "USDT",
        "price_precision": 2,
        "quantity_precision": 8,
        "timezone": "UTC",
        "calendar_kind": CalendarKind.ALWAYS_OPEN,
        "trading_calendar": "crypto-24x7",
        "is_enabled": True,
        "metadata_version": 1,
    }
    values.update(overrides)
    return CanonicalInstrument(**values)  # type: ignore[arg-type]


def test_valid_spot_pair_uses_canonical_identity_separate_from_provider_symbol() -> None:
    instrument = make_instrument(symbol="BTC/USDT")

    assert instrument.slug == "btc-usdt"
    assert instrument.symbol == "BTC/USDT"
    assert not hasattr(instrument, "provider_symbol")


@pytest.mark.parametrize("slug", ["BTC-USDT", "btc_usdt", "btc--usdt", "btc-usdt-"])
def test_invalid_slug_is_rejected(slug: str) -> None:
    with pytest.raises(ValueError, match="slug"):
        make_instrument(slug=slug)


def test_invalid_timezone_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone"):
        make_instrument(timezone="Mars/Olympus")


@pytest.mark.parametrize("price_precision", [-1, 16])
def test_invalid_precision_is_rejected(price_precision: int) -> None:
    with pytest.raises(ValueError, match="precision"):
        make_instrument(price_precision=price_precision)


def test_non_positive_metadata_version_is_rejected() -> None:
    with pytest.raises(ValueError, match="metadata_version"):
        make_instrument(metadata_version=0)


def test_spot_pair_requires_base_and_quote_assets() -> None:
    with pytest.raises(ValueError, match="base_asset and quote_asset"):
        make_instrument(base_asset=None)


@pytest.mark.parametrize("asset_class", [AssetClass.CRYPTO_SPOT, AssetClass.METAL_FX_SPOT])
def test_spot_asset_classes_require_spot_market_type(asset_class: AssetClass) -> None:
    with pytest.raises(ValueError, match="spot"):
        make_instrument(asset_class=asset_class, market_type=MarketType.REFERENCE_INDEX)


def test_index_and_yield_semantics_do_not_require_crypto_pair_fields() -> None:
    index = make_instrument(
        asset_class=AssetClass.EQUITY_INDEX,
        market_type=MarketType.REFERENCE_INDEX,
        base_asset=None,
        quote_asset=None,
        calendar_kind=CalendarKind.EXCHANGE,
        trading_calendar="future-equity-reference",
    )
    yield_reference = make_instrument(
        asset_class=AssetClass.GOVERNMENT_YIELD,
        market_type=MarketType.YIELD_REFERENCE,
        base_asset=None,
        quote_asset=None,
        calendar_kind=CalendarKind.REFERENCE_DATA,
        trading_calendar="future-yield-reference",
    )

    assert index.base_asset is None
    assert yield_reference.quote_asset is None
