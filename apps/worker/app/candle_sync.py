from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any, cast

import asyncpg
from pepe_quote_core import CandleTimeframe, FakeHistoricalCandleProvider, NormalizedCandle
from redis import asyncio as redis_asyncio

from app.candle_redis import CandleRedisLeaseStore, RedisClient
from app.candle_sync_service import (
    CandleSyncRetryable,
    CandleSyncService,
    CandleSyncSkipped,
    CandleSyncSuccess,
    CandleSyncTarget,
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

    async def upsert(self, candle: NormalizedCandle) -> bool:
        command_tag = await self._connection.execute(
            """
            INSERT INTO market_candles (
                id, instrument_id, timeframe, open_time, close_time, open, high, low, close,
                base_volume, quote_volume, trade_count, source_label, venue_label, received_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
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
            """,
            uuid.uuid4(),
            candle.instrument_id,
            candle.timeframe.value,
            candle.open_time,
            candle.close_time,
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.base_volume,
            candle.quote_volume,
            candle.trade_count,
            candle.source_label,
            candle.venue_label,
            candle.received_at,
        )
        return str(command_tag).endswith(" 1")

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


async def sync_fake_candles() -> dict[str, int | str]:
    if not worker_settings.quote_fake_provider_enabled:
        return {"status": "disabled", "synced": 0}
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
            now = datetime.now(UTC)
            service = CandleSyncService(
                leases=CandleRedisLeaseStore(
                    cast(RedisClient, redis),
                    lease_ttl_seconds=worker_settings.candle_sync_lease_ttl_seconds,
                ),
                provider=FakeHistoricalCandleProvider(clock=lambda: now),
                unit_of_work_factory=AsyncpgCandleUnitOfWorkFactory(connection),
            )
            results = [await service.sync(target, now) for target in targets]
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
