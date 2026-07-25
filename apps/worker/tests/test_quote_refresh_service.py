from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime

import pytest
from pepe_quote_core import FakeQuoteProvider, NormalizedQuote, QuoteRequest

from app.quote_refresh_service import (
    QuoteRefreshService,
    RefreshRetryable,
    RefreshSkipped,
    RefreshSuccess,
    RefreshTarget,
    RetryReason,
    SkipReason,
)


class FakeLeases:
    def __init__(
        self, events: list[str], *, acquired: bool = True, fail_acquire: bool = False,
    ) -> None:
        self.events = events
        self.acquired = acquired
        self.fail_acquire = fail_acquire
        self.release_tokens: list[str] = []

    async def acquire_refresh_lease(self, instrument_id: uuid.UUID, owner_token: str) -> bool:
        self.events.append(f"acquire:{instrument_id}:{owner_token}")
        if self.fail_acquire:
            raise OSError("redis unavailable")
        return self.acquired

    async def release_refresh_lease(self, instrument_id: uuid.UUID, owner_token: str) -> bool:
        self.events.append(f"release:{instrument_id}:{owner_token}")
        self.release_tokens.append(owner_token)
        return True


class FakeProvider:
    def __init__(
        self, events: list[str], quote: NormalizedQuote, *, fail: bool = False,
    ) -> None:
        self.events = events
        self.quote = quote
        self.fail = fail

    async def fetch_quotes(self, requests: Iterable[QuoteRequest]) -> tuple[NormalizedQuote, ...]:
        self.events.append("provider")
        assert len(tuple(requests)) == 1
        if self.fail:
            raise TimeoutError("provider timed out")
        return (self.quote,)


class FakeUnitOfWork:
    def __init__(self, events: list[str], *, fail_commit: bool = False) -> None:
        self.events = events
        self.fail_commit = fail_commit

    async def upsert(self, quote: NormalizedQuote) -> None:
        del quote
        self.events.append("upsert")

    async def commit(self) -> None:
        self.events.append("commit")
        if self.fail_commit:
            raise OSError("database unavailable")

    async def rollback(self) -> None:
        self.events.append("rollback")


class FakeUnitOfWorkFactory:
    def __init__(self, events: list[str], *, fail_commit: bool = False) -> None:
        self.events = events
        self.unit_of_work = FakeUnitOfWork(events, fail_commit=fail_commit)

    async def create(self) -> FakeUnitOfWork:
        self.events.append("create_uow")
        return self.unit_of_work


class FakeCache:
    def __init__(self, events: list[str], *, fail: bool = False) -> None:
        self.events = events
        self.fail = fail

    async def set_cached_quote(self, quote: NormalizedQuote) -> None:
        del quote
        self.events.append("cache")
        if self.fail:
            raise OSError("cache unavailable")


async def _quote_and_target() -> tuple[NormalizedQuote, RefreshTarget]:
    instrument_id = uuid.uuid4()
    request = QuoteRequest(
        instrument_id=instrument_id,
        instrument_slug="btc-usdt",
        provider_key="fake",
        provider_mapping_id=uuid.uuid4(),
        provider_instrument_id="test-btc-usdt",
        mapping_version=1,
    )
    provider = FakeQuoteProvider(clock=lambda: datetime(2026, 1, 1, tzinfo=UTC))
    quote = (await provider.fetch_quotes((request,)))[0]
    return quote, RefreshTarget(request)


def _service(
    leases: FakeLeases,
    provider: FakeProvider,
    unit_of_work_factory: FakeUnitOfWorkFactory,
    cache: FakeCache,
) -> QuoteRefreshService:
    return QuoteRefreshService(
        leases=leases,
        provider=provider,
        unit_of_work_factory=unit_of_work_factory,
        cache=cache,
        owner_token_factory=lambda: "test-owner",
    )


@pytest.mark.asyncio
async def test_refresh_orders_lease_provider_uow_commit_cache_and_owner_safe_release() -> None:
    events: list[str] = []
    quote, target = await _quote_and_target()
    leases = FakeLeases(events)
    service = _service(
        leases,
        FakeProvider(events, quote),
        FakeUnitOfWorkFactory(events),
        FakeCache(events),
    )

    result = await service.refresh(target)

    assert result == RefreshSuccess(target.instrument_id, cache_written=True)
    assert events == [
        f"acquire:{target.instrument_id}:test-owner",
        "provider",
        "create_uow",
        "upsert",
        "commit",
        "cache",
        f"release:{target.instrument_id}:test-owner",
    ]
    assert leases.release_tokens == ["test-owner"]


@pytest.mark.asyncio
async def test_busy_lease_skips_without_provider_or_release() -> None:
    events: list[str] = []
    quote, target = await _quote_and_target()
    service = _service(
        FakeLeases(events, acquired=False),
        FakeProvider(events, quote),
        FakeUnitOfWorkFactory(events),
        FakeCache(events),
    )

    result = await service.refresh(target)

    assert result == RefreshSkipped(target.instrument_id, SkipReason.LEASE_HELD)
    assert events == [f"acquire:{target.instrument_id}:test-owner"]


@pytest.mark.asyncio
async def test_lease_failure_is_retryable_and_suppresses_provider() -> None:
    events: list[str] = []
    quote, target = await _quote_and_target()
    service = _service(
        FakeLeases(events, fail_acquire=True),
        FakeProvider(events, quote),
        FakeUnitOfWorkFactory(events),
        FakeCache(events),
    )

    result = await service.refresh(target)

    assert result == RefreshRetryable(target.instrument_id, RetryReason.LEASE_UNAVAILABLE)
    assert events == [f"acquire:{target.instrument_id}:test-owner"]


@pytest.mark.asyncio
async def test_commit_failure_rolls_back_and_still_releases_lease() -> None:
    events: list[str] = []
    quote, target = await _quote_and_target()
    service = _service(
        FakeLeases(events),
        FakeProvider(events, quote),
        FakeUnitOfWorkFactory(events, fail_commit=True),
        FakeCache(events),
    )

    result = await service.refresh(target)

    assert result == RefreshRetryable(target.instrument_id, RetryReason.PERSISTENCE_FAILED)
    assert events == [
        f"acquire:{target.instrument_id}:test-owner",
        "provider",
        "create_uow",
        "upsert",
        "commit",
        "rollback",
        f"release:{target.instrument_id}:test-owner",
    ]


@pytest.mark.asyncio
async def test_cache_failure_after_commit_remains_success_and_releases_lease() -> None:
    events: list[str] = []
    quote, target = await _quote_and_target()
    service = _service(
        FakeLeases(events),
        FakeProvider(events, quote),
        FakeUnitOfWorkFactory(events),
        FakeCache(events, fail=True),
    )

    result = await service.refresh(target)

    assert result == RefreshSuccess(target.instrument_id, cache_written=False)
    assert events == [
        f"acquire:{target.instrument_id}:test-owner",
        "provider",
        "create_uow",
        "upsert",
        "commit",
        "cache",
        f"release:{target.instrument_id}:test-owner",
    ]
