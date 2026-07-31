from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any, cast

import asyncpg
from pepe_quote_core import (
    CandleTimeframe,
    FakeHistoricalCandleProvider,
    MarketDataMode,
    NormalizedCandle,
)
from redis import asyncio as redis_asyncio

from app.candle_redis import CandleRedisLeaseStore, RedisClient
from app.candle_sync_service import (
    CandleSyncRetryable,
    CandleSyncService,
    CandleSyncSkipped,
    CandleSyncSuccess,
    CandleSyncTarget,
    HistoricalCandleProvider,
)
from app.config import worker_settings


class AsyncpgCandleUnitOfWork:
    """Explicit transaction adapter for market_candles; it imports no API application code."""

    def __init__(self, connection: asyncpg.Connection[Any], transaction: Any) -> None:
        self._connection = connection
        self._transaction = transaction

    async def latest_open_time(
        self,
        instrument_id: uuid.UUID,
        timeframe: CandleTimeframe,
    ) -> datetime | None:
        return cast(
            datetime | None,
            await self._connection.fetchval(
                """
                SELECT max(open_time) FROM market_candles
                WHERE instrument_id = $1 AND timeframe = $2
                """,
                instrument_id,
                timeframe.value,
            ),
        )

    async def upsert_many(self, candles: tuple[NormalizedCandle, ...]) -> int:
        """Upsert one fetched page-set in a single PostgreSQL statement."""
        if not candles:
            return 0
        rows = await self._connection.fetch(
            """
            INSERT INTO market_candles (
                id, instrument_id, timeframe, open_time, close_time, open, high, low, close,
                base_volume, quote_volume, trade_count, source_label, venue_label, received_at
            )
            SELECT * FROM UNNEST(
                $1::uuid[], $2::uuid[], $3::text[], $4::timestamptz[], $5::timestamptz[],
                $6::numeric[], $7::numeric[], $8::numeric[], $9::numeric[], $10::numeric[],
                $11::numeric[], $12::integer[], $13::text[], $14::text[], $15::timestamptz[]
            ) ON CONFLICT (instrument_id, timeframe, open_time) DO UPDATE SET
                close_time = EXCLUDED.close_time,
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                base_volume = EXCLUDED.base_volume,
                quote_volume = EXCLUDED.quote_volume,
                trade_count = EXCLUDED.trade_count,
                source_label = EXCLUDED.source_label,
                venue_label = EXCLUDED.venue_label,
                received_at = EXCLUDED.received_at,
                updated_at = now()
            RETURNING 1
            """,
            [uuid.uuid4() for _ in candles],
            [candle.instrument_id for candle in candles],
            [candle.timeframe.value for candle in candles],
            [candle.open_time for candle in candles],
            [candle.close_time for candle in candles],
            [candle.open for candle in candles],
            [candle.high for candle in candles],
            [candle.low for candle in candles],
            [candle.close for candle in candles],
            [candle.base_volume for candle in candles],
            [candle.quote_volume for candle in candles],
            [candle.trade_count for candle in candles],
            [candle.source_label for candle in candles],
            [candle.venue_label for candle in candles],
            [candle.received_at for candle in candles],
        )
        return len(rows)

    async def commit(self) -> None:
        await self._transaction.commit()

    async def rollback(self) -> None:
        await self._transaction.rollback()


class AsyncpgCandleUnitOfWorkFactory:
    def __init__(self, connection: asyncpg.Connection[Any]) -> None:
        self._connection = connection

    async def create(self) -> AsyncpgCandleUnitOfWork:
        transaction = self._connection.transaction()
        await transaction.start()
        return AsyncpgCandleUnitOfWork(self._connection, transaction)


async def sync_candles(
    provider: HistoricalCandleProvider,
    *,
    now: datetime | None = None,
) -> dict[str, int | str]:
    """Compose worker infrastructure around any historical-candle provider."""
    connection = await asyncpg.connect(
        worker_settings.database_url.replace("+asyncpg", ""),
        timeout=10,
        command_timeout=10,
    )
    try:
        redis = redis_asyncio.from_url(
            worker_settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        try:
            targets = await _load_targets(connection)
            sync_time = now or datetime.now(UTC)
            service = CandleSyncService(
                leases=CandleRedisLeaseStore(
                    cast(RedisClient, redis),
                    lease_ttl_seconds=worker_settings.candle_sync_lease_ttl_seconds,
                ),
                provider=provider,
                unit_of_work_factory=AsyncpgCandleUnitOfWorkFactory(connection),
            )
            results = [await service.sync(target, sync_time) for target in targets]
            retryable = [result for result in results if isinstance(result, CandleSyncRetryable)]
            if retryable:
                reasons = ", ".join(sorted({result.reason.value for result in retryable}))
                raise OSError(f"candle sync retryable failures: {reasons}")
            return {
                "status": "ok",
                "synced": sum(isinstance(result, CandleSyncSuccess) for result in results),
                "skipped": sum(isinstance(result, CandleSyncSkipped) for result in results),
            }
        finally:
            await redis.aclose()
    finally:
        await connection.close()


async def sync_fake_candles() -> dict[str, int | str]:
    """Run the explicitly enabled local-development fake provider."""
    if worker_settings.market_data_mode is not MarketDataMode.DEMO:
        raise RuntimeError(
            "synthetic candle synchronization is forbidden outside market_data_mode=demo",
        )
    if not worker_settings.candle_fake_provider_enabled:
        return {"status": "disabled", "synced": 0}
    now = datetime.now(UTC)
    return await sync_candles(FakeHistoricalCandleProvider(clock=lambda: now), now=now)


async def _load_targets(connection: asyncpg.Connection[Any]) -> tuple[CandleSyncTarget, ...]:
    rows = await connection.fetch(
        """
        SELECT id, slug FROM asset_instruments
        WHERE is_enabled AND slug = ANY($1::text[])
        ORDER BY slug
        """,
        ["btc-usdt", "eth-usdt", "xau-usd"],
    )
    return tuple(
        CandleSyncTarget(row["id"], row["slug"], timeframe)
        for row in rows
        for timeframe in CandleTimeframe
    )


def run_sync_fake_candles() -> dict[str, int | str]:
    return asyncio.run(sync_fake_candles())
