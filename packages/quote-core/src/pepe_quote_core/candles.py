from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from itertools import pairwise

from .types import _validate_magnitude, _validate_utc_timestamp


class CandleTimeframe(StrEnum):
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"


@dataclass(frozen=True, slots=True)
class CandleRequest:
    """Provider-neutral request for closed candles, inclusive at both boundaries."""

    instrument_id: uuid.UUID
    instrument_slug: str
    timeframe: CandleTimeframe
    from_time: datetime
    to_time: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", uuid.UUID(str(self.instrument_id)))
        _validate_utc_timestamp("from_time", self.from_time)
        _validate_utc_timestamp("to_time", self.to_time)
        if not self.instrument_slug:
            raise ValueError("instrument_slug must not be empty")
        if self.from_time > self.to_time:
            raise ValueError("from_time must not be after to_time")
        duration = timeframe_duration(self.timeframe)
        for name, value in (("from_time", self.from_time), ("to_time", self.to_time)):
            if int(value.timestamp()) % int(duration.total_seconds()) != 0:
                raise ValueError(f"{name} must align to timeframe boundary")


_TIMEFRAME_DURATIONS = {
    CandleTimeframe.ONE_MINUTE: timedelta(minutes=1),
    CandleTimeframe.FIVE_MINUTES: timedelta(minutes=5),
    CandleTimeframe.FIFTEEN_MINUTES: timedelta(minutes=15),
    CandleTimeframe.ONE_HOUR: timedelta(hours=1),
    CandleTimeframe.FOUR_HOURS: timedelta(hours=4),
    CandleTimeframe.ONE_DAY: timedelta(days=1),
}

_BOOTSTRAP_WINDOWS = {
    CandleTimeframe.ONE_MINUTE: timedelta(hours=24),
    CandleTimeframe.FIVE_MINUTES: timedelta(days=7),
    CandleTimeframe.FIFTEEN_MINUTES: timedelta(days=30),
    CandleTimeframe.ONE_HOUR: timedelta(days=180),
    CandleTimeframe.FOUR_HOURS: timedelta(days=365),
    CandleTimeframe.ONE_DAY: timedelta(days=365 * 5),
}


def timeframe_duration(timeframe: CandleTimeframe) -> timedelta:
    return _TIMEFRAME_DURATIONS[timeframe]


def bootstrap_window(timeframe: CandleTimeframe) -> timedelta:
    return _BOOTSTRAP_WINDOWS[timeframe]


def align_open_time(timestamp: datetime, timeframe: CandleTimeframe) -> datetime:
    _validate_utc_timestamp("timestamp", timestamp)
    duration_seconds = int(timeframe_duration(timeframe).total_seconds())
    return datetime.fromtimestamp(
        timestamp.timestamp() // duration_seconds * duration_seconds, tz=timestamp.tzinfo,
    )


def latest_closed_open_time(now: datetime, timeframe: CandleTimeframe) -> datetime:
    """Return the opening boundary of the newest fully closed candle."""
    _validate_utc_timestamp("now", now)
    return align_open_time(now, timeframe) - timeframe_duration(timeframe)


def incremental_from(latest_open_time: datetime, timeframe: CandleTimeframe) -> datetime:
    _validate_utc_timestamp("latest_open_time", latest_open_time)
    return latest_open_time - 2 * timeframe_duration(timeframe)


def detect_gaps(
    open_times: tuple[datetime, ...], timeframe: CandleTimeframe,
) -> tuple[datetime, ...]:
    if not open_times:
        return ()
    duration = timeframe_duration(timeframe)
    ordered = sorted(set(open_times))
    gaps: list[datetime] = []
    for previous, current in pairwise(ordered):
        candidate = previous + duration
        while candidate < current:
            gaps.append(candidate)
            candidate += duration
    return tuple(gaps)


@dataclass(frozen=True, slots=True)
class NormalizedCandle:
    instrument_id: uuid.UUID
    timeframe: CandleTimeframe
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    base_volume: Decimal | None
    quote_volume: Decimal | None
    trade_count: int | None
    source_label: str
    venue_label: str | None
    received_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", uuid.UUID(str(self.instrument_id)))
        timestamps = (
            ("open_time", self.open_time),
            ("close_time", self.close_time),
            ("received_at", self.received_at),
        )
        for name, timestamp in timestamps:
            _validate_utc_timestamp(name, timestamp)
        duration = timeframe_duration(self.timeframe)
        if self.close_time != self.open_time + duration:
            raise ValueError("close_time must equal open_time plus timeframe duration")
        if int(self.open_time.timestamp()) % int(duration.total_seconds()) != 0:
            raise ValueError("open_time must align to timeframe boundary")
        if self.received_at < self.close_time:
            raise ValueError("received_at must not precede close_time")
        ohlc = (("open", self.open), ("high", self.high), ("low", self.low), ("close", self.close))
        for name, value in ohlc:
            _validate_magnitude(name, value)
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must bound open, close, and low")
        if self.low > min(self.open, self.close):
            raise ValueError("low must not exceed open or close")
        volumes = (("base_volume", self.base_volume), ("quote_volume", self.quote_volume))
        for name, amount in volumes:
            if amount is not None:
                _validate_magnitude(name, amount)
                if amount < 0:
                    raise ValueError(f"{name} must not be negative")
        if self.trade_count is not None and self.trade_count < 0:
            raise ValueError("trade_count must not be negative")
        if not self.source_label:
            raise ValueError("source_label must not be empty")
