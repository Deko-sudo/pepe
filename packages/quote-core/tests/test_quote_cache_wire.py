from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

import pytest

from pepe_quote_core import (
    CachePayloadError,
    CurrentQuoteCacheEntry,
    DataStatus,
    DelayClass,
    MarketStatus,
    MarketType,
    PriceType,
    PublicProvenance,
    decode_current_quote_cache,
    encode_current_quote_cache,
)


def _entry() -> CurrentQuoteCacheEntry:
    return CurrentQuoteCacheEntry(
        slug="btc-usdt",
        price=Decimal("60000.00"),
        bid=Decimal("59999.50"),
        ask=Decimal("60000.50"),
        mid=Decimal("60000.00"),
        open_24h=Decimal("59000.00"),
        high_24h=Decimal("61000.00"),
        low_24h=Decimal("58000.00"),
        change_24h=Decimal("1000.00"),
        change_percent_24h=Decimal("1.69"),
        base_volume_24h=Decimal("12.50"),
        quote_volume_24h=Decimal("750000.00"),
        market_status=MarketStatus.OPEN,
        data_status=DataStatus.FRESH,
        observed_at=datetime(2026, 7, 25, tzinfo=UTC),
        received_at=datetime(2026, 7, 25, tzinfo=UTC),
        age_seconds=0,
        provenance=PublicProvenance(
            source_label="Synthetic test source",
            venue_label="Synthetic test venue",
            market_type=MarketType.SPOT,
            price_type=PriceType.LAST_TRADE,
            delay_class=DelayClass.REALTIME,
        ),
    )


def _wire() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(encode_current_quote_cache(_entry())))


def test_current_quote_cache_round_trip_is_canonical_and_matches_api_wire_shape() -> None:
    entry = _entry()

    encoded = encode_current_quote_cache(entry)
    wire = json.loads(encoded)

    assert encoded == encode_current_quote_cache(decode_current_quote_cache(encoded))
    assert decode_current_quote_cache(encoded) == entry
    assert set(wire) == {"schema_version", "quote"}
    assert wire["schema_version"] == 1
    assert set(wire["quote"]) == {
        "slug", "price", "bid", "ask", "mid", "open_24h", "high_24h", "low_24h",
        "change_24h", "change_percent_24h", "base_volume_24h", "quote_volume_24h",
        "market_status", "data_status", "observed_at", "received_at", "age_seconds", "provenance",
    }
    assert "instrument_id" not in wire["quote"]
    assert wire["quote"]["provenance"] == {
        "source_label": "Synthetic test source",
        "venue_label": "Synthetic test venue",
        "market_type": "spot",
        "price_type": "last_trade",
        "delay_class": "realtime",
    }


def test_current_quote_cache_rejects_flattened_provenance() -> None:
    wire = _wire()
    quote = wire["quote"]
    provenance = quote.pop("provenance")
    quote.update(provenance)

    with pytest.raises(CachePayloadError):
        decode_current_quote_cache(json.dumps(wire))


@pytest.mark.parametrize(
    "payload",
    [
        "{",
        b"\xff",
        1,
        "[]",
        '{"schema_version":2,"quote":{}}',
        '{"schema_version":1,"quote":{},"extra":true}',
        '{"schema_version":1,"quote":{"slug":"one","slug":"two"}}',
        '{"schema_version":1,"quote":NaN}',
        '{"schema_version":true,"quote":{}}',
    ],
)
def test_current_quote_cache_all_invalid_input_types_raise_cache_payload_error(
    payload: object,
) -> None:
    with pytest.raises(CachePayloadError):
        decode_current_quote_cache(payload)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("price",), 1),
        (("price",), "NaN"),
        (("price",), "100000000000000000001"),
        (("age_seconds",), True),
        (("observed_at",), "2026-07-25T00:00:00"),
        (("market_status",), "not-a-status"),
        (("provenance", "venue_label"), ""),
        (("provenance", "delay_class"), "not-a-delay-class"),
    ],
)
def test_current_quote_cache_invalid_field_values_raise_cache_payload_error(
    path: tuple[str, ...], value: object,
) -> None:
    wire = _wire()
    target: dict[str, Any] = wire["quote"]
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value

    with pytest.raises(CachePayloadError):
        decode_current_quote_cache(json.dumps(wire))
