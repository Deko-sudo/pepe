from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import asyncpg
import pytest
from pepe_quote_core import CandleRequest, CandleTimeframe, NormalizedCandle
from redis import asyncio as redis_asyncio

from app.candle_redis import CandleRedisLeaseStore
from app.candle_sync import AsyncpgCandleUnitOfWorkFactory
from app.candle_sync_service import (
    CandleSyncRetryable,
    CandleSyncRetryReason,
    CandleSyncService,
    CandleSyncSkipped,
    CandleSyncSkipReason,
    CandleSyncSuccess,
    CandleSyncTarget,
    CandleUnitOfWork,
    CandleUnitOfWorkFactory,
    HistoricalCandleProvider,
)

pytestmark = pytest.mark.skipif(
    not (os.getenv("TEST_DATABASE_URL") and os.getenv("TEST_REDIS_URL")),
    reason="requires TEST_DATABASE_URL and TEST_REDIS_URL from the isolated Stage 7 harness",
)

_BTC_USDT_ID = uuid.UUID("a6d8c260-3f98-4d19-9e87-8dd33413b401")
_NOW = datetime(2026, 1, 8, 12, tzinfo=UTC)
_TARGET = CandleSyncTarget(_BTC_USDT_ID, "btc-usdt", CandleTimeframe.ONE_MINUTE)


@dataclass(frozen=True, slots=True)
class IntegrationResources:
    connection: asyncpg.Connection[Any]
    redis: Any


@pytest.fixture
async def integration_resources() -> AsyncIterator[IntegrationResources]:
    connection = await asyncpg.connect(os.environ["TEST_DATABASE_URL"].replace("+asyncpg", ""))
    redis = redis_asyncio.from_url(os.environ["TEST_REDIS_URL"], decode_responses=True)
    try:
        await connection.execute(
            "DELETE FROM market_candles WHERE instrument_id = $1", _BTC_USDT_ID,
        )
        await redis.delete(
            CandleRedisLeaseStore.lease_key(_BTC_USDT_ID, CandleTimeframe.ONE_MINUTE),
        )
        yield IntegrationResources(connection, redis)
    finally:
        await connection.execute(
            "DELETE FROM market_candles WHERE instrument_id = $1", _BTC_USDT_ID,
        )
        await redis.delete(
            CandleRedisLeaseStore.lease_key(_BTC_USDT_ID, CandleTimeframe.ONE_MINUTE),
        )
        await redis.aclose()
        await connection.close()


def _candle(*, close: Decimal, source_label: str) -> NormalizedCandle:
    open_time = _NOW - timedelta(minutes=5)
    return NormalizedCandle(
        instrument_id=_BTC_USDT_ID,
        timeframe=CandleTimeframe.ONE_MINUTE,
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=close,
        base_volume=Decimal("3"),
        quote_volume=Decimal("300"),
        trade_count=7,
        source_label=source_label,
        venue_label="stage7-it",
        received_at=_NOW,
    )


def _open_times(request: CandleRequest) -> tuple[datetime, ...]:
    step = timedelta(minutes=1)
    return tuple(
        request.from_time + step * index
        for index in range(int((request.to_time - request.from_time) / step) + 1)
    )


class StaticProvider:
    def __init__(self, candle: NormalizedCandle) -> None:
        self.candle = candle
        self.calls = 0

    async def fetch_candles(self, request: CandleRequest) -> tuple[NormalizedCandle, ...]:
        self.calls += 1
        return tuple(
            replace(
                self.candle,
                open_time=open_time,
                close_time=open_time + timedelta(minutes=1),
            )
            for open_time in _open_times(request)
        )


class BlockingProvider(StaticProvider):
    def __init__(
        self,
        candle: NormalizedCandle,
        started: asyncio.Event,
        release: asyncio.Event,
    ) -> None:
        super().__init__(candle)
        self._started = started
        self._release = release

    async def fetch_candles(self, request: CandleRequest) -> tuple[NormalizedCandle, ...]:
        self._started.set()
        await self._release.wait()
        return await super().fetch_candles(request)


class CommitFailingUnitOfWork:
    def __init__(self, inner: CandleUnitOfWork) -> None:
        self._inner = inner

    async def latest_open_time(
        self, instrument_id: uuid.UUID, timeframe: CandleTimeframe,
    ) -> object | None:
        return await self._inner.latest_open_time(instrument_id, timeframe)

    async def upsert(self, candle: NormalizedCandle) -> bool:
        return await self._inner.upsert(candle)

    async def commit(self) -> None:
        raise OSError("injected commit failure")

    async def rollback(self) -> None:
        await self._inner.rollback()


class CommitFailingUnitOfWorkFactory:
    def __init__(self, inner: CandleUnitOfWorkFactory) -> None:
        self._inner = inner

    async def create(self) -> CommitFailingUnitOfWork:
        return CommitFailingUnitOfWork(await self._inner.create())


def _service(
    resources: IntegrationResources,
    provider: HistoricalCandleProvider,
    unit_of_work_factory: CandleUnitOfWorkFactory | None = None,
) -> CandleSyncService:
    return CandleSyncService(
        leases=CandleRedisLeaseStore(resources.redis, lease_ttl_seconds=300),
        provider=provider,
        unit_of_work_factory=unit_of_work_factory
        or AsyncpgCandleUnitOfWorkFactory(resources.connection),
        owner_token_factory=lambda: str(uuid.uuid4()),
    )


@pytest.mark.asyncio
async def test_migration_is_at_stage7_head_with_market_candles_schema(
    integration_resources: IntegrationResources,
) -> None:
    assert (
        await integration_resources.connection.fetchval("SELECT version_num FROM alembic_version")
        == "007"
    )
    assert await integration_resources.connection.fetchval(
        "SELECT to_regclass('public.market_candles')",
    ) == "market_candles"
    constraints = await integration_resources.connection.fetch(
        """
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'market_candles'::regclass
        ORDER BY conname
        """,
    )
    assert "uq_market_candles_identity" in {row["conname"] for row in constraints}


@pytest.mark.asyncio
async def test_real_postgres_persists_idempotently_and_applies_candle_revision(
    integration_resources: IntegrationResources,
) -> None:
    initial_provider = StaticProvider(_candle(close=Decimal("105"), source_label="initial"))
    initial_result = await _service(integration_resources, initial_provider).sync(_TARGET, _NOW)

    revised_provider = StaticProvider(_candle(close=Decimal("106"), source_label="revised"))
    revised_result = await _service(integration_resources, revised_provider).sync(_TARGET, _NOW)

    row = await integration_resources.connection.fetchrow(
        """
        SELECT count(*) OVER () AS count, close, source_label
        FROM market_candles
        WHERE instrument_id = $1 AND timeframe = $2
        ORDER BY open_time DESC
        """,
        _BTC_USDT_ID,
        CandleTimeframe.ONE_MINUTE.value,
    )
    assert initial_result == CandleSyncSuccess(
        _BTC_USDT_ID,
        CandleTimeframe.ONE_MINUTE,
        written=1441,
    )
    assert revised_result == CandleSyncSuccess(_BTC_USDT_ID, CandleTimeframe.ONE_MINUTE, written=3)
    assert initial_provider.calls == 3
    assert revised_provider.calls == 1
    assert row is not None
    assert row["count"] == 1441
    assert row["close"] == Decimal("106")
    assert row["source_label"] == "revised"


@pytest.mark.asyncio
async def test_real_postgres_rolls_back_when_commit_fails(
    integration_resources: IntegrationResources,
) -> None:
    result = await _service(
        integration_resources,
        StaticProvider(_candle(close=Decimal("105"), source_label="rollback")),
        CommitFailingUnitOfWorkFactory(AsyncpgCandleUnitOfWorkFactory(integration_resources.connection)),
    ).sync(_TARGET, _NOW)

    assert result == CandleSyncRetryable(
        _BTC_USDT_ID,
        CandleTimeframe.ONE_MINUTE,
        CandleSyncRetryReason.PERSISTENCE_FAILED,
    )
    assert await integration_resources.connection.fetchval(
        "SELECT count(*) FROM market_candles WHERE instrument_id = $1",
        _BTC_USDT_ID,
    ) == 0


@pytest.mark.asyncio
async def test_real_redis_owner_safe_lease_and_concurrent_sync_single_flight(
    integration_resources: IntegrationResources,
) -> None:
    leases = CandleRedisLeaseStore(integration_resources.redis, lease_ttl_seconds=300)
    assert await leases.acquire(_BTC_USDT_ID, CandleTimeframe.ONE_MINUTE, "owner-a") is True
    ttl = await integration_resources.redis.ttl(
        CandleRedisLeaseStore.lease_key(_BTC_USDT_ID, CandleTimeframe.ONE_MINUTE),
    )
    assert 295 <= ttl <= 300
    assert await leases.acquire(_BTC_USDT_ID, CandleTimeframe.ONE_MINUTE, "owner-b") is False
    assert await leases.release(_BTC_USDT_ID, CandleTimeframe.ONE_MINUTE, "owner-b") is False
    assert await leases.release(_BTC_USDT_ID, CandleTimeframe.ONE_MINUTE, "owner-a") is True

    started = asyncio.Event()
    release = asyncio.Event()
    provider = BlockingProvider(
        _candle(close=Decimal("105"), source_label="concurrent"), started, release,
    )
    first = _service(integration_resources, provider)
    second = _service(integration_resources, provider)
    first_task = asyncio.create_task(first.sync(_TARGET, _NOW))
    try:
        await asyncio.wait_for(started.wait(), timeout=2)
        second_result = await asyncio.wait_for(second.sync(_TARGET, _NOW), timeout=2)
        release.set()
        first_result = await asyncio.wait_for(first_task, timeout=2)
    finally:
        release.set()
        if not first_task.done():
            first_task.cancel()
            with suppress(asyncio.CancelledError):
                await first_task

    assert first_result == CandleSyncSuccess(
        _BTC_USDT_ID,
        CandleTimeframe.ONE_MINUTE,
        written=1441,
    )
    assert second_result == CandleSyncSkipped(
        _BTC_USDT_ID,
        CandleTimeframe.ONE_MINUTE,
        CandleSyncSkipReason.LEASE_HELD,
    )
    assert provider.calls == 3
