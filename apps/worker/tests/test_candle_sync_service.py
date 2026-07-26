from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pepe_quote_core import (
    CandleRequest,
    CandleTimeframe,
    FakeHistoricalCandleProvider,
    NormalizedCandle,
)

from app.candle_sync_service import (
    CandleSyncRetryable,
    CandleSyncRetryReason,
    CandleSyncService,
    CandleSyncSuccess,
    CandleSyncTarget,
)


class Leases:
    def __init__(self, events: list[str], acquired: bool = True) -> None:
        self.events = events
        self.acquired = acquired

    async def acquire(
        self,
        instrument_id: uuid.UUID,
        timeframe: CandleTimeframe,
        owner_token: str,
    ) -> bool:
        self.events.append(f"acquire:{owner_token}")
        return self.acquired

    async def release(
        self,
        instrument_id: uuid.UUID,
        timeframe: CandleTimeframe,
        owner_token: str,
    ) -> bool:
        self.events.append(f"release:{owner_token}")
        return True


class Uow:
    def __init__(self, events: list[str], latest: datetime | None = None) -> None:
        self.events = events
        self.latest = latest
        self.candles: list[NormalizedCandle] = []

    async def latest_open_time(
        self, instrument_id: uuid.UUID, timeframe: CandleTimeframe,
    ) -> datetime | None:
        self.events.append("latest")
        return self.latest

    async def upsert(self, candle: NormalizedCandle) -> bool:
        self.events.append("upsert")
        self.candles.append(candle)
        return True

    async def commit(self) -> None:
        self.events.append("commit")

    async def rollback(self) -> None:
        self.events.append("rollback")


class Factory:
    def __init__(self, uow: Uow) -> None:
        self.uow = uow

    async def create(self) -> Uow:
        self.uow.events.append("create")
        return self.uow


class Provider:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.requests: list[CandleRequest] = []

    async def fetch_candles(self, request: CandleRequest) -> tuple[NormalizedCandle, ...]:
        self.events.append("provider")
        self.requests.append(request)
        return ()


@pytest.mark.asyncio
async def test_bootstrap_uses_exact_elapsed_window_and_owner_safe_lifecycle() -> None:
    events: list[str] = []
    provider = Provider(events)
    target = CandleSyncTarget(uuid.uuid4(), "btc-usdt", CandleTimeframe.FIVE_MINUTES)
    uow = Uow(events)
    now = datetime(2026, 1, 8, 12, 0, tzinfo=UTC)
    service = CandleSyncService(
        leases=Leases(events),
        provider=provider,
        unit_of_work_factory=Factory(uow),
        owner_token_factory=lambda: "owner",
    )

    result = await service.sync(target, now)

    assert result == CandleSyncSuccess(target.instrument_id, target.timeframe, written=0)
    assert provider.requests
    assert provider.requests[0].from_time == datetime(2026, 1, 1, 11, 55, tzinfo=UTC)
    assert provider.requests[-1].to_time == datetime(2026, 1, 8, 11, 55, tzinfo=UTC)
    assert all(
        request.to_time - request.from_time <= timedelta(minutes=5 * 499)
        for request in provider.requests
    )
    assert events[0:3] == ["acquire:owner", "create", "latest"]
    assert events[-2:] == ["commit", "release:owner"]


@pytest.mark.asyncio
async def test_incremental_sync_refetches_two_candle_overlap() -> None:
    events: list[str] = []
    provider = Provider(events)
    target = CandleSyncTarget(uuid.uuid4(), "eth-usdt", CandleTimeframe.ONE_HOUR)
    latest = datetime(2026, 1, 8, 8, tzinfo=UTC)
    service = CandleSyncService(
        leases=Leases(events),
        provider=provider,
        unit_of_work_factory=Factory(Uow(events, latest)),
        owner_token_factory=lambda: "owner",
    )

    await service.sync(target, datetime(2026, 1, 8, 12, 30, tzinfo=UTC))

    assert provider.requests
    assert provider.requests[0].from_time == datetime(2026, 1, 8, 6, tzinfo=UTC)
    assert provider.requests[-1].to_time == datetime(2026, 1, 8, 11, tzinfo=UTC)


@pytest.mark.asyncio
async def test_provider_failure_is_retryable_and_releases_lease() -> None:
    class FailingProvider(Provider):
        async def fetch_candles(self, request: CandleRequest) -> tuple[NormalizedCandle, ...]:
            raise TimeoutError

    events: list[str] = []
    target = CandleSyncTarget(uuid.uuid4(), "xau-usd", CandleTimeframe.ONE_DAY)
    service = CandleSyncService(
        leases=Leases(events),
        provider=FailingProvider(events),
        unit_of_work_factory=Factory(Uow(events)),
        owner_token_factory=lambda: "owner",
    )

    result = await service.sync(target, datetime(2026, 1, 8, tzinfo=UTC))

    assert result == CandleSyncRetryable(
        target.instrument_id,
        target.timeframe,
        CandleSyncRetryReason.PROVIDER_FAILED,
    )
    assert events == ["acquire:owner", "create", "latest", "rollback", "release:owner"]


@pytest.mark.asyncio
@pytest.mark.parametrize("instrument_slug", ["btc-usdt", "eth-usdt", "xau-usd"])
@pytest.mark.parametrize("timeframe", list(CandleTimeframe))
async def test_fake_provider_supports_each_required_instrument_and_timeframe(
    timeframe: CandleTimeframe, instrument_slug: str,
) -> None:
    provider = FakeHistoricalCandleProvider(clock=lambda: datetime(2026, 1, 2, tzinfo=UTC))
    request = CandleRequest(
        instrument_id=uuid.uuid4(),
        instrument_slug=instrument_slug,
        timeframe=timeframe,
        from_time=datetime(2026, 1, 1, tzinfo=UTC),
        to_time=datetime(2026, 1, 1, tzinfo=UTC),
    )
    candle = (await provider.fetch_candles(request))[0]
    assert candle.close == Decimal("59995.25") or candle.close > 0
