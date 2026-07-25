from __future__ import annotations

import uuid
from collections.abc import Awaitable
from contextlib import suppress
from decimal import Decimal
from typing import Protocol, cast

import redis.asyncio as aioredis
from pepe_quote_core import (
    CurrentQuoteCacheEntry,
    PublicProvenance,
    decode_current_quote_cache,
    encode_current_quote_cache,
)

from app.core.config import settings
from app.schemas.quotes import CurrentQuoteResponse


class RedisClient(Protocol):
    def get(self, name: str) -> Awaitable[str | bytes | None]: ...

    def set(self, name: str, value: str, *, ex: int) -> Awaitable[None]: ...

    def aclose(self) -> Awaitable[None]: ...


class CurrentQuoteCache:
    """Best-effort UUID-keyed cache. Invalid values and Redis failures are misses."""

    def __init__(self, *, client: RedisClient | None = None) -> None:
        self._client = client or cast(
            RedisClient,
            aioredis.from_url(settings.quote_cache_url, socket_connect_timeout=2),
        )

    async def get(self, instrument_id: uuid.UUID) -> CurrentQuoteResponse | None:
        try:
            raw = await self._client.get(self._key(instrument_id))
            if raw is None:
                return None
            return _response_from_entry(decode_current_quote_cache(raw))
        except Exception:
            return None

    async def set(self, instrument_id: uuid.UUID, quote: CurrentQuoteResponse) -> None:
        payload = encode_current_quote_cache(_entry_from_response(quote))
        with suppress(Exception):
            await self._client.set(
                self._key(instrument_id),
                payload,
                ex=settings.quote_cache_ttl_seconds,
            )

    async def close(self) -> None:
        with suppress(Exception):
            await self._client.aclose()

    @staticmethod
    def _key(instrument_id: uuid.UUID) -> str:
        return f"{settings.quote_cache_namespace}:{instrument_id}"


def _entry_from_response(quote: CurrentQuoteResponse) -> CurrentQuoteCacheEntry:
    return CurrentQuoteCacheEntry(
        slug=quote.slug,
        price=Decimal(quote.price),
        bid=None if quote.bid is None else Decimal(quote.bid),
        ask=None if quote.ask is None else Decimal(quote.ask),
        mid=None if quote.mid is None else Decimal(quote.mid),
        open_24h=None if quote.open_24h is None else Decimal(quote.open_24h),
        high_24h=None if quote.high_24h is None else Decimal(quote.high_24h),
        low_24h=None if quote.low_24h is None else Decimal(quote.low_24h),
        change_24h=None if quote.change_24h is None else Decimal(quote.change_24h),
        change_percent_24h=(
            None if quote.change_percent_24h is None else Decimal(quote.change_percent_24h)
        ),
        base_volume_24h=None if quote.base_volume_24h is None else Decimal(quote.base_volume_24h),
        quote_volume_24h=(
            None if quote.quote_volume_24h is None else Decimal(quote.quote_volume_24h)
        ),
        market_status=quote.market_status,
        data_status=quote.data_status,
        observed_at=quote.observed_at,
        received_at=quote.received_at,
        age_seconds=quote.age_seconds,
        provenance=PublicProvenance(
            source_label=quote.provenance.source_label,
            venue_label=quote.provenance.venue_label,
            market_type=quote.provenance.market_type,
            price_type=quote.provenance.price_type,
            delay_class=quote.provenance.delay_class,
        ),
    )


def _response_from_entry(entry: CurrentQuoteCacheEntry) -> CurrentQuoteResponse:
    return CurrentQuoteResponse.from_values(
        slug=entry.slug,
        price=entry.price,
        bid=entry.bid,
        ask=entry.ask,
        mid=entry.mid,
        open_24h=entry.open_24h,
        high_24h=entry.high_24h,
        low_24h=entry.low_24h,
        change_24h=entry.change_24h,
        change_percent_24h=entry.change_percent_24h,
        base_volume_24h=entry.base_volume_24h,
        quote_volume_24h=entry.quote_volume_24h,
        market_status=entry.market_status,
        data_status=entry.data_status,
        observed_at=entry.observed_at,
        received_at=entry.received_at,
        age_seconds=entry.age_seconds,
        market_type=entry.provenance.market_type,
        price_type=entry.provenance.price_type,
        delay_class=entry.provenance.delay_class,
        source_label=entry.provenance.source_label,
        venue_label=entry.provenance.venue_label,
    )
