from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol, TypeAlias

from pepe_quote_core import (
    CandleRequest,
    CandleTimeframe,
    NormalizedCandle,
    bootstrap_window,
    detect_gaps,
    incremental_from,
    latest_closed_open_time,
    timeframe_duration,
)

logger = logging.getLogger(__name__)


class CandleLeaseStore(Protocol):
    async def acquire(
        self,
        instrument_id: uuid.UUID,
        timeframe: CandleTimeframe,
        owner_token: str,
    ) -> bool: ...

    async def release(
        self,
        instrument_id: uuid.UUID,
        timeframe: CandleTimeframe,
        owner_token: str,
    ) -> bool: ...


class HistoricalCandleProvider(Protocol):
    async def fetch_candles(self, request: CandleRequest) -> tuple[NormalizedCandle, ...]: ...


class CandleUnitOfWork(Protocol):
    async def latest_open_time(
        self,
        instrument_id: uuid.UUID,
        timeframe: CandleTimeframe,
    ) -> object | None: ...

    async def upsert(self, candle: NormalizedCandle) -> bool: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class CandleUnitOfWorkFactory(Protocol):
    async def create(self) -> CandleUnitOfWork: ...


@dataclass(frozen=True, slots=True)
class CandleSyncTarget:
    instrument_id: uuid.UUID
    instrument_slug: str
    timeframe: CandleTimeframe


class CandleSyncSkipReason(StrEnum):
    LEASE_HELD = "lease_held"


class CandleSyncRetryReason(StrEnum):
    LEASE_UNAVAILABLE = "lease_unavailable"
    PROVIDER_FAILED = "provider_failed"
    INVALID_PROVIDER_RESPONSE = "invalid_provider_response"
    PERSISTENCE_FAILED = "persistence_failed"


@dataclass(frozen=True, slots=True)
class CandleSyncSuccess:
    instrument_id: uuid.UUID
    timeframe: CandleTimeframe
    written: int


@dataclass(frozen=True, slots=True)
class CandleSyncSkipped:
    instrument_id: uuid.UUID
    timeframe: CandleTimeframe
    reason: CandleSyncSkipReason


@dataclass(frozen=True, slots=True)
class CandleSyncRetryable:
    instrument_id: uuid.UUID
    timeframe: CandleTimeframe
    reason: CandleSyncRetryReason


CandleSyncResult: TypeAlias = CandleSyncSuccess | CandleSyncSkipped | CandleSyncRetryable  # noqa: UP040


class CandleSyncService:
    """Synchronize one instrument/timeframe under a short, owner-safe Redis lease."""

    def __init__(
        self,
        *,
        leases: CandleLeaseStore,
        provider: HistoricalCandleProvider,
        unit_of_work_factory: CandleUnitOfWorkFactory,
        owner_token_factory: Callable[[], str] | None = None,
    ) -> None:
        self._leases = leases
        self._provider = provider
        self._unit_of_work_factory = unit_of_work_factory
        self._owner_token_factory = owner_token_factory or (lambda: str(uuid.uuid4()))

    async def sync(self, target: CandleSyncTarget, now: datetime) -> CandleSyncResult:
        # The public core helpers validate that now is an aware UTC datetime.
        owner_token = self._owner_token_factory()
        try:
            acquired = await self._leases.acquire(
                target.instrument_id,
                target.timeframe,
                owner_token,
            )
        except Exception:
            return CandleSyncRetryable(
                target.instrument_id,
                target.timeframe,
                CandleSyncRetryReason.LEASE_UNAVAILABLE,
            )
        if not acquired:
            return CandleSyncSkipped(
                target.instrument_id,
                target.timeframe,
                CandleSyncSkipReason.LEASE_HELD,
            )

        try:
            unit_of_work: CandleUnitOfWork | None = None
            try:
                unit_of_work = await self._unit_of_work_factory.create()
                latest = await unit_of_work.latest_open_time(target.instrument_id, target.timeframe)
                latest_time = latest if isinstance(latest, datetime) else None
                newest_closed = latest_closed_open_time(now, target.timeframe)
                if latest_time is None:
                    # Use elapsed (not calendar) windows and retain only closed candles.
                    from_time = newest_closed + (bootstrap_window(target.timeframe) * -1)
                else:
                    from_time = incremental_from(latest_time, target.timeframe)
                request = CandleRequest(
                    instrument_id=target.instrument_id,
                    instrument_slug=target.instrument_slug,
                    timeframe=target.timeframe,
                    from_time=from_time,
                    to_time=newest_closed,
                )
                try:
                    candles = await self._fetch_pages(target, request)
                except Exception:
                    await unit_of_work.rollback()
                    return CandleSyncRetryable(
                        target.instrument_id,
                        target.timeframe,
                        CandleSyncRetryReason.PROVIDER_FAILED,
                    )
                if candles is None:
                    await unit_of_work.rollback()
                    return CandleSyncRetryable(
                        target.instrument_id,
                        target.timeframe,
                        CandleSyncRetryReason.INVALID_PROVIDER_RESPONSE,
                    )
                written = 0
                for candle in candles:
                    written += await unit_of_work.upsert(candle)
                await unit_of_work.commit()
            except Exception:
                if unit_of_work is not None:
                    try:
                        await unit_of_work.rollback()
                    except Exception:
                        logger.warning("candle sync rollback failed", exc_info=True)
                return CandleSyncRetryable(
                    target.instrument_id,
                    target.timeframe,
                    CandleSyncRetryReason.PERSISTENCE_FAILED,
                )
            return CandleSyncSuccess(target.instrument_id, target.timeframe, written)
        finally:
            try:
                await self._leases.release(target.instrument_id, target.timeframe, owner_token)
            except Exception:
                logger.warning("candle sync lease release failed", exc_info=True)

    async def _fetch_pages(
        self,
        target: CandleSyncTarget,
        request: CandleRequest,
    ) -> tuple[NormalizedCandle, ...] | None:
        """Fetch bounded, monotonic pages and reject gaps or malformed provider output."""
        interval = timeframe_duration(target.timeframe)
        max_page_candles = 500
        cursor = request.from_time
        deduplicated: dict[datetime, NormalizedCandle] = {}
        while cursor <= request.to_time:
            page_to = min(cursor + interval * (max_page_candles - 1), request.to_time)
            page_request = CandleRequest(
                instrument_id=request.instrument_id,
                instrument_slug=request.instrument_slug,
                timeframe=request.timeframe,
                from_time=cursor,
                to_time=page_to,
            )
            page = await self._provider.fetch_candles(page_request)
            if not page and page_to != request.to_time:
                return None
            if not self._valid_response(target, request, page):
                return None
            for candle in page:
                existing = deduplicated.get(candle.open_time)
                if existing is not None and existing != candle:
                    return None
                deduplicated[candle.open_time] = candle
            cursor = page_to + interval

        open_times = tuple(sorted(deduplicated))
        if not open_times:
            return ()
        if detect_gaps(open_times, target.timeframe):
            return None
        return tuple(deduplicated[open_time] for open_time in open_times)

    @staticmethod
    def _valid_response(
        target: CandleSyncTarget,
        request: CandleRequest,
        candles: tuple[NormalizedCandle, ...],
    ) -> bool:
        return all(
            candle.instrument_id == target.instrument_id
            and candle.timeframe == target.timeframe
            and request.from_time <= candle.open_time <= request.to_time
            for candle in candles
        )
