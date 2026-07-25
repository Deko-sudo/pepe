from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import asyncpg
from pepe_quote_core import (
    CurrentQuoteCacheEntry,
    FakeQuoteProvider,
    NormalizedQuote,
    QuoteRequest,
    encode_current_quote_cache,
)
from redis import asyncio as redis_asyncio

from app.config import worker_settings
from app.quote_redis import QuoteRedisStore
from app.quote_refresh_service import (
    QuoteRefreshService,
    RefreshRetryable,
    RefreshSkipped,
    RefreshSuccess,
    RefreshTarget,
)

_FAKE_MAPPING_IDS = {
    "btc-usdt": uuid.UUID("90bcf405-eefd-4c18-9fb4-df4c1c7f0ee1"),
    "eth-usdt": uuid.UUID("0713b5cd-0015-4c90-8ef6-4c798b4c7319"),
    "xau-usd": uuid.UUID("5a1e811e-4987-458a-b348-b10dcff0e4d8"),
}


class AsyncpgQuoteUnitOfWork:
    """One explicit asyncpg transaction for a durable quote upsert."""

    def __init__(
        self,
        connection: asyncpg.Connection[Any],
        transaction: Any,
    ) -> None:
        self._connection = connection
        self._transaction = transaction

    async def upsert(self, quote: NormalizedQuote) -> None:
        await self._connection.execute(
            """
            INSERT INTO latest_market_quotes (
                instrument_id, provider_mapping_id, provider_key, provider_instrument_id,
                source_venue, market_type, price_type, price, bid, ask, mid,
                provider_timestamp, observed_at, received_at, data_delay_seconds,
                market_status, delay_class, mapping_version, schema_version, provider_event_id
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                $12, $13, $14, $15, $16, $17, $18, $19, $20
            )
            ON CONFLICT (instrument_id) DO UPDATE SET
                provider_mapping_id = EXCLUDED.provider_mapping_id,
                provider_key = EXCLUDED.provider_key,
                provider_instrument_id = EXCLUDED.provider_instrument_id,
                source_venue = EXCLUDED.source_venue,
                market_type = EXCLUDED.market_type,
                price_type = EXCLUDED.price_type,
                price = EXCLUDED.price,
                bid = EXCLUDED.bid,
                ask = EXCLUDED.ask,
                mid = EXCLUDED.mid,
                provider_timestamp = EXCLUDED.provider_timestamp,
                observed_at = EXCLUDED.observed_at,
                received_at = EXCLUDED.received_at,
                data_delay_seconds = EXCLUDED.data_delay_seconds,
                market_status = EXCLUDED.market_status,
                delay_class = EXCLUDED.delay_class,
                mapping_version = EXCLUDED.mapping_version,
                schema_version = EXCLUDED.schema_version,
                provider_event_id = EXCLUDED.provider_event_id
            WHERE EXCLUDED.observed_at > latest_market_quotes.observed_at
               OR (
                   EXCLUDED.observed_at = latest_market_quotes.observed_at
                   AND EXCLUDED.provider_event_id > COALESCE(
                       latest_market_quotes.provider_event_id, ''
                   )
            )
            """,
            quote.instrument_id,
            quote.provider_mapping_id,
            quote.provider_key,
            quote.provider_instrument_id,
            quote.source_venue,
            quote.market_type.value,
            quote.price_type.value,
            quote.price,
            quote.bid,
            quote.ask,
            quote.mid,
            quote.provider_timestamp,
            quote.observed_at,
            quote.received_at,
            quote.data_delay_seconds,
            quote.market_status.value,
            quote.delay_class.value,
            quote.mapping_version,
            quote.schema_version,
            quote.provider_event_id,
        )

    async def commit(self) -> None:
        await self._transaction.commit()

    async def rollback(self) -> None:
        await self._transaction.rollback()


class AsyncpgQuoteUnitOfWorkFactory:
    """Starts explicit transactions; callers decide when to commit or roll back."""

    def __init__(self, connection: asyncpg.Connection[Any]) -> None:
        self._connection = connection

    async def create(self) -> AsyncpgQuoteUnitOfWork:
        transaction = self._connection.transaction()
        await transaction.start()
        return AsyncpgQuoteUnitOfWork(self._connection, transaction)


class RedisQuoteCache:
    def __init__(self, store: QuoteRedisStore) -> None:
        self._store = store

    async def set_cached_quote(self, quote: NormalizedQuote) -> None:
        payload = encode_current_quote_cache(
            CurrentQuoteCacheEntry(
                slug=quote.instrument_slug,
                price=quote.price,
                bid=quote.bid,
                ask=quote.ask,
                mid=quote.mid,
                open_24h=quote.open_24h,
                high_24h=quote.high_24h,
                low_24h=quote.low_24h,
                change_24h=quote.change_24h,
                change_percent_24h=quote.change_percent_24h,
                base_volume_24h=quote.base_volume_24h,
                quote_volume_24h=quote.quote_volume_24h,
                market_status=quote.market_status,
                data_status=quote.data_status,
                observed_at=quote.observed_at,
                received_at=quote.received_at,
                age_seconds=max(0, int((quote.received_at - quote.observed_at).total_seconds())),
                provenance=quote.provenance,
            ),
        )
        await self._store.set_cached_quote(quote.instrument_id, payload)


async def refresh_fake_quotes() -> dict[str, int | str]:
    """Compose worker adapters around the dependency-injected refresh service."""
    if not worker_settings.quote_fake_provider_enabled:
        return {"status": "disabled", "refreshed": 0}

    connection = await asyncpg.connect(
        worker_settings.database_url.replace("+asyncpg", ""),
        timeout=10,
        command_timeout=10,
    )
    try:
        redis = redis_asyncio.from_url(
            worker_settings.quote_cache_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        try:
            await _ensure_fake_mappings(connection)
            targets = await _load_fake_targets(connection)
            now = datetime.now(UTC)
            store = QuoteRedisStore(
                redis,
                cache_namespace=worker_settings.quote_cache_namespace,
                cache_ttl_seconds=worker_settings.quote_cache_ttl_seconds,
                lease_ttl_seconds=worker_settings.quote_refresh_lease_ttl_seconds,
            )
            service = QuoteRefreshService(
                leases=store,
                provider=FakeQuoteProvider(clock=lambda: now),
                unit_of_work_factory=AsyncpgQuoteUnitOfWorkFactory(connection),
                cache=RedisQuoteCache(store),
            )
            results = await service.refresh_many(targets)
            retryable = [result for result in results if isinstance(result, RefreshRetryable)]
            if retryable:
                reasons = ", ".join(sorted({result.reason.value for result in retryable}))
                raise OSError(f"quote refresh retryable failures: {reasons}")
            return {
                "status": "ok",
                "refreshed": sum(isinstance(result, RefreshSuccess) for result in results),
                "skipped": sum(isinstance(result, RefreshSkipped) for result in results),
            }
        finally:
            await redis.aclose()
    finally:
        await connection.close()


async def _load_fake_targets(connection: asyncpg.Connection[Any]) -> tuple[RefreshTarget, ...]:
    rows = await connection.fetch(
        """
        SELECT ai.id AS instrument_id, ai.slug, pim.id AS mapping_id, pim.provider_key,
               pim.provider_symbol, pim.mapping_version
        FROM asset_instruments ai
        JOIN provider_instrument_mappings pim ON pim.instrument_id = ai.id
        WHERE ai.is_enabled AND pim.is_enabled AND pim.provider_key = 'fake'
        ORDER BY ai.slug
        """,
    )
    return tuple(
        RefreshTarget(
            QuoteRequest(
                instrument_id=row["instrument_id"],
                instrument_slug=row["slug"],
                provider_key=row["provider_key"],
                provider_mapping_id=row["mapping_id"],
                provider_instrument_id=row["provider_symbol"],
                mapping_version=row["mapping_version"],
            ),
        )
        for row in rows
    )


async def _ensure_fake_mappings(connection: asyncpg.Connection[Any]) -> None:
    for slug, mapping_id in _FAKE_MAPPING_IDS.items():
        await connection.execute(
            """
            INSERT INTO provider_instrument_mappings (
                id, instrument_id, provider_key, provider_symbol, provider_market,
                is_enabled, priority, mapping_version
            )
            SELECT $1, id, 'fake', $2, 'synthetic', true, 1, 1
            FROM asset_instruments
            WHERE slug = $3
            ON CONFLICT DO NOTHING
            """,
            mapping_id,
            f"test-{slug}",
            slug,
        )


def run_refresh_fake_quotes() -> dict[str, int | str]:
    return asyncio.run(refresh_fake_quotes())
