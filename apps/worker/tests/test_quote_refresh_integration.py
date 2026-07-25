from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator, Iterable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import asyncpg
import pytest
from pepe_quote_core import FakeQuoteProvider, NormalizedQuote, QuoteRequest
from redis import asyncio as redis_asyncio

from app.quote_redis import QuoteRedisStore
from app.quote_refresh import AsyncpgQuoteUnitOfWorkFactory, RedisQuoteCache
from app.quote_refresh_service import (
    QuoteProvider,
    QuoteRefreshService,
    QuoteUnitOfWork,
    QuoteUnitOfWorkFactory,
    RefreshRetryable,
    RefreshSkipped,
    RefreshSuccess,
    RefreshTarget,
    RetryReason,
    SkipReason,
)

pytestmark = pytest.mark.skipif(
    not (os.getenv("TEST_DATABASE_URL") and os.getenv("TEST_REDIS_URL")),
    reason="requires TEST_DATABASE_URL and TEST_REDIS_URL from the isolated Stage 6 harness",
)

_BTC_USDT_ID = uuid.UUID("a6d8c260-3f98-4d19-9e87-8dd33413b401")


@dataclass(frozen=True, slots=True)
class IntegrationResources:
    connection: asyncpg.Connection[Any]
    redis: Any
    target: RefreshTarget
    cache_namespace: str


@pytest.fixture
async def integration_resources() -> AsyncIterator[IntegrationResources]:
    database_url = os.environ["TEST_DATABASE_URL"].replace("+asyncpg", "")
    connection = await asyncpg.connect(database_url)
    redis = redis_asyncio.from_url(os.environ["TEST_REDIS_URL"], decode_responses=True)
    mapping_id = uuid.uuid4()
    cache_namespace = f"stage6:test:{uuid.uuid4()}"
    await connection.execute(
        """
        INSERT INTO provider_instrument_mappings (
            id, instrument_id, provider_key, provider_symbol, provider_market,
            is_enabled, priority, mapping_version
        ) VALUES ($1, $2, 'stage6-test', $3, 'synthetic', true, 100, 1)
        """,
        mapping_id,
        _BTC_USDT_ID,
        f"test-{mapping_id}",
    )
    target = RefreshTarget(
        QuoteRequest(
            instrument_id=_BTC_USDT_ID,
            instrument_slug="btc-usdt",
            provider_key="stage6-test",
            provider_mapping_id=mapping_id,
            provider_instrument_id=f"test-{mapping_id}",
            mapping_version=1,
        ),
    )
    try:
        yield IntegrationResources(connection, redis, target, cache_namespace)
    finally:
        await connection.execute(
            "DELETE FROM latest_market_quotes WHERE instrument_id = $1",
            _BTC_USDT_ID,
        )
        await connection.execute(
            "DELETE FROM provider_instrument_mappings WHERE id = $1",
            mapping_id,
        )
        await redis.aclose()
        await connection.close()


def _service(
    resources: IntegrationResources,
    provider: QuoteProvider,
    unit_of_work_factory: QuoteUnitOfWorkFactory,
) -> QuoteRefreshService:
    store = QuoteRedisStore(
        resources.redis,
        cache_namespace=resources.cache_namespace,
        cache_ttl_seconds=60,
        lease_ttl_seconds=30,
    )
    return QuoteRefreshService(
        leases=store,
        provider=provider,
        unit_of_work_factory=unit_of_work_factory,
        cache=RedisQuoteCache(store),
        owner_token_factory=lambda: str(uuid.uuid4()),
    )


class CommitFailingUnitOfWork:
    """Test-only fault injector: failure occurs before the wrapped transaction commits."""

    def __init__(self, inner: QuoteUnitOfWork) -> None:
        self._inner = inner

    async def upsert(self, quote: NormalizedQuote) -> None:
        await self._inner.upsert(quote)

    async def commit(self) -> None:
        raise OSError("injected commit failure")

    async def rollback(self) -> None:
        await self._inner.rollback()


class CommitFailingUnitOfWorkFactory:
    """Test-only UoW factory wrapper for durable commit-failure coverage."""

    def __init__(self, inner: QuoteUnitOfWorkFactory) -> None:
        self._inner = inner

    async def create(self) -> CommitFailingUnitOfWork:
        return CommitFailingUnitOfWork(await self._inner.create())


class BlockingProvider:
    def __init__(
        self,
        quote: NormalizedQuote,
        started: asyncio.Event,
        release: asyncio.Event,
    ) -> None:
        self._quote = quote
        self._started = started
        self._release = release
        self.calls = 0

    async def fetch_quotes(self, requests: Iterable[QuoteRequest]) -> tuple[NormalizedQuote, ...]:
        assert len(tuple(requests)) == 1
        self.calls += 1
        self._started.set()
        await self._release.wait()
        return (self._quote,)


async def _quote(target: RefreshTarget) -> NormalizedQuote:
    provider = FakeQuoteProvider(clock=lambda: datetime(2026, 1, 1, tzinfo=UTC))
    return (await provider.fetch_quotes((target.request,)))[0]


@pytest.mark.asyncio
async def test_real_redis_lease_rejects_second_owner_and_preserves_owner_safety(
    integration_resources: IntegrationResources,
) -> None:
    store = QuoteRedisStore(
        integration_resources.redis,
        cache_namespace=integration_resources.cache_namespace,
        cache_ttl_seconds=60,
        lease_ttl_seconds=30,
    )
    instrument_id = integration_resources.target.instrument_id

    assert await store.acquire_refresh_lease(instrument_id, "owner-a") is True
    assert await store.acquire_refresh_lease(instrument_id, "owner-b") is False
    assert await store.release_refresh_lease(instrument_id, "owner-b") is False
    assert await store.release_refresh_lease(instrument_id, "owner-a") is True


@pytest.mark.asyncio
async def test_commit_failure_rolls_back_and_never_writes_cache(
    integration_resources: IntegrationResources,
) -> None:
    quote = await _quote(integration_resources.target)
    service = _service(
        integration_resources,
        FakeQuoteProvider(clock=lambda: datetime(2026, 1, 1, tzinfo=UTC)),
        CommitFailingUnitOfWorkFactory(
            AsyncpgQuoteUnitOfWorkFactory(integration_resources.connection),
        ),
    )

    result = await service.refresh(integration_resources.target)

    assert result == RefreshRetryable(
        integration_resources.target.instrument_id,
        RetryReason.PERSISTENCE_FAILED,
    )
    assert (
        await integration_resources.connection.fetchval(
            "SELECT count(*) FROM latest_market_quotes WHERE instrument_id = $1",
            integration_resources.target.instrument_id,
        )
        == 0
    )
    assert (
        await integration_resources.redis.get(
            f"{integration_resources.cache_namespace}:{quote.instrument_id}",
        )
        is None
    )


@pytest.mark.asyncio
async def test_concurrent_refreshes_have_one_provider_call_and_one_lease_skip(
    integration_resources: IntegrationResources,
) -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    provider = BlockingProvider(await _quote(integration_resources.target), started, release)
    factory = AsyncpgQuoteUnitOfWorkFactory(integration_resources.connection)
    first = _service(integration_resources, provider, factory)
    second = _service(integration_resources, provider, factory)
    first_task = asyncio.create_task(first.refresh(integration_resources.target))
    try:
        await asyncio.wait_for(started.wait(), timeout=2)
        second_result = await asyncio.wait_for(
            second.refresh(integration_resources.target),
            timeout=2,
        )
        release.set()
        first_result = await asyncio.wait_for(first_task, timeout=2)
    finally:
        release.set()
        if not first_task.done():
            first_task.cancel()
            with suppress(asyncio.CancelledError):
                await first_task

    assert first_result == RefreshSuccess(
        integration_resources.target.instrument_id,
        cache_written=True,
    )
    assert second_result == RefreshSkipped(
        integration_resources.target.instrument_id,
        SkipReason.LEASE_HELD,
    )
    assert provider.calls == 1
