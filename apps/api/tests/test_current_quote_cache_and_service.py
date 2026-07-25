from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import pytest
from pepe_quote_core import (
    DataStatus,
    DelayClass,
    MarketStatus,
    MarketType,
    PriceType,
    decode_current_quote_cache,
    encode_current_quote_cache,
)

from app.modules.market_data.quote_cache import CurrentQuoteCache, _entry_from_response
from app.modules.market_data.quotes import CurrentQuoteService
from app.schemas.quotes import CurrentQuoteResponse

INSTRUMENT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
NOW = datetime(2026, 7, 25, 12, tzinfo=UTC)


def make_response(**overrides: object) -> CurrentQuoteResponse:
    values: dict[str, object] = {
        "slug": "btc-usdt",
        "price": Decimal("60000.00"),
        "bid": Decimal("59999.50"),
        "ask": Decimal("60000.50"),
        "mid": Decimal("60000.00"),
        "open_24h": Decimal("59000.00"),
        "high_24h": Decimal("61000.00"),
        "low_24h": Decimal("58000.00"),
        "change_24h": Decimal("1000.00"),
        "change_percent_24h": Decimal("1.69"),
        "base_volume_24h": Decimal("12.50"),
        "quote_volume_24h": Decimal("750000.00"),
        "market_status": MarketStatus.OPEN,
        "data_status": DataStatus.FRESH,
        "observed_at": NOW,
        "received_at": NOW,
        "age_seconds": 0,
        "market_type": MarketType.SPOT,
        "price_type": PriceType.LAST_TRADE,
        "delay_class": DelayClass.REALTIME,
        "source_label": "Synthetic test source",
        "venue_label": "Synthetic test venue",
    }
    values.update(overrides)
    return CurrentQuoteResponse.from_values(**values)  # type: ignore[arg-type]


def invalid_cache_payload(kind: str) -> str:
    if kind == "malformed":
        return "not json"
    wire = json.loads(encode_current_quote_cache(_entry_from_response(make_response())))
    if kind == "unsupported-version":
        wire["schema_version"] = 2
    elif kind == "flattened-provenance":
        quote = cast(dict[str, Any], wire["quote"])
        quote.update(quote.pop("provenance"))
    else:
        raise AssertionError(f"unexpected invalid-payload kind: {kind}")
    return json.dumps(wire)


class FakeRedis:
    def __init__(self, value: str | bytes | None = None, *, error: Exception | None = None) -> None:
        self.value = value
        self.error = error
        self.calls: list[tuple[object, ...]] = []

    async def get(self, name: str) -> str | bytes | None:
        self.calls.append(("get", name))
        if self.error is not None:
            raise self.error
        return self.value

    async def set(self, name: str, value: str, *, ex: int) -> None:
        self.calls.append(("set", name, value, ex))
        if self.error is not None:
            raise self.error

    async def aclose(self) -> None:
        self.calls.append(("aclose",))
        if self.error is not None:
            raise self.error


class FakeResult:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value


class FakeDatabase:
    def __init__(self, *values: object | None) -> None:
        self._values = list(values)
        self.calls: list[object] = []

    async def execute(self, statement: object) -> FakeResult:
        self.calls.append(statement)
        if not self._values:
            raise AssertionError("the cache hit must not query durable quotes")
        return FakeResult(self._values.pop(0))


class FakeCache:
    def __init__(self, value: CurrentQuoteResponse | None) -> None:
        self.value = value
        self.get_calls: list[uuid.UUID] = []
        self.set_calls: list[tuple[uuid.UUID, CurrentQuoteResponse]] = []
        self.closed = False

    async def get(self, instrument_id: uuid.UUID) -> CurrentQuoteResponse | None:
        self.get_calls.append(instrument_id)
        return self.value

    async def set(self, instrument_id: uuid.UUID, quote: CurrentQuoteResponse) -> None:
        self.set_calls.append((instrument_id, quote))

    async def close(self) -> None:
        self.closed = True


def make_instrument() -> SimpleNamespace:
    return SimpleNamespace(id=INSTRUMENT_ID, slug="btc-usdt", asset_class="crypto_spot")


def make_durable_quote() -> SimpleNamespace:
    return SimpleNamespace(
        price=Decimal("60000.00"), bid=Decimal("59999.50"), ask=Decimal("60000.50"),
        mid=Decimal("60000.00"), open_24h=Decimal("59000.00"), high_24h=Decimal("61000.00"),
        low_24h=Decimal("58000.00"), change_24h=Decimal("1000.00"),
        change_percent_24h=Decimal("1.69"), base_volume_24h=Decimal("12.50"),
        quote_volume_24h=Decimal("750000.00"), market_status="open", observed_at=NOW,
        received_at=NOW, market_type="spot", price_type="last_trade", delay_class="realtime",
    )


@pytest.mark.asyncio
async def test_cache_restores_a_shared_codec_v1_payload_with_nested_provenance() -> None:
    response = make_response()
    redis = FakeRedis(encode_current_quote_cache(_entry_from_response(response)))
    cache = CurrentQuoteCache(client=redis)

    restored = await cache.get(INSTRUMENT_ID)

    assert restored == response
    assert redis.calls == [("get", cache._key(INSTRUMENT_ID))]
    assert restored.provenance.model_dump(mode="json") == {
        "source_label": "Synthetic test source", "venue_label": "Synthetic test venue",
        "market_type": "spot", "price_type": "last_trade", "delay_class": "realtime",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["malformed", "unsupported-version", "flattened-provenance"])
async def test_cache_treats_invalid_or_flattened_payloads_as_misses(kind: str) -> None:
    cache = CurrentQuoteCache(client=FakeRedis(invalid_cache_payload(kind)))

    assert await cache.get(INSTRUMENT_ID) is None


@pytest.mark.asyncio
async def test_cache_set_uses_the_shared_v1_codec_and_nested_provenance() -> None:
    redis = FakeRedis()
    cache = CurrentQuoteCache(client=redis)
    response = make_response()

    await cache.set(INSTRUMENT_ID, response)

    _, key, _, expiry = redis.calls[0]
    payload = cast(str, redis.calls[0][2])
    assert key == cache._key(INSTRUMENT_ID)
    assert expiry == 60
    assert payload == encode_current_quote_cache(_entry_from_response(response))
    decoded = decode_current_quote_cache(payload)
    assert decoded.provenance.source_label == "Synthetic test source"
    assert decoded.provenance.venue_label == "Synthetic test venue"


@pytest.mark.asyncio
async def test_cache_swallows_redis_get_set_and_close_exceptions() -> None:
    cache = CurrentQuoteCache(client=FakeRedis(error=RuntimeError("redis unavailable")))

    assert await cache.get(INSTRUMENT_ID) is None
    await cache.set(INSTRUMENT_ID, make_response())
    await cache.close()


@pytest.mark.asyncio
async def test_service_cache_hit_avoids_the_durable_quote_database_query() -> None:
    cached = make_response()
    cache = FakeCache(cached)
    db = FakeDatabase(make_instrument())

    result = await CurrentQuoteService(cache=cache).get_current_quote_by_slug(
        cast(Any, db),
        "btc-usdt",
        now=NOW,
    )

    assert result == cached
    assert len(db.calls) == 1
    assert cache.get_calls == [INSTRUMENT_ID]
    assert cache.set_calls == []
    assert cache.closed is True


@pytest.mark.asyncio
async def test_service_cache_miss_falls_back_to_durable_quote_and_restores_cache() -> None:
    cache = FakeCache(None)
    db = FakeDatabase(make_instrument(), make_durable_quote())

    result = await CurrentQuoteService(cache=cache).get_current_quote_by_slug(
        cast(Any, db),
        "btc-usdt",
        now=NOW,
    )

    assert result == make_response()
    assert len(db.calls) == 2
    assert cache.set_calls == [(INSTRUMENT_ID, make_response())]
    assert cache.closed is True


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["malformed", "unsupported-version", "flattened-provenance"])
async def test_service_invalid_cache_payload_falls_back_to_durable_quote(kind: str) -> None:
    redis = FakeRedis(invalid_cache_payload(kind))
    db = FakeDatabase(make_instrument(), make_durable_quote())

    service = CurrentQuoteService(cache=CurrentQuoteCache(client=redis))
    result = await service.get_current_quote_by_slug(
        cast(Any, db),
        "btc-usdt",
        now=NOW,
    )

    assert result == make_response()
    assert len(db.calls) == 2
    assert redis.calls[0][0] == "get"
    assert redis.calls[1][0] == "set"
