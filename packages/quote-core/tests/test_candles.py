from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from pepe_quote_core import (
    CandleRequest,
    CandleTimeframe,
    FakeHistoricalCandleProvider,
    FakeQuoteProvider,
    NormalizedCandle,
    align_open_time,
    bootstrap_window,
    detect_gaps,
    incremental_from,
    latest_closed_open_time,
    timeframe_duration,
)


@pytest.mark.parametrize(
    ("timeframe", "seconds"),
    [
        (CandleTimeframe.ONE_MINUTE, 60),
        (CandleTimeframe.FIVE_MINUTES, 300),
        (CandleTimeframe.FIFTEEN_MINUTES, 900),
        (CandleTimeframe.ONE_HOUR, 3600),
        (CandleTimeframe.FOUR_HOURS, 14400),
        (CandleTimeframe.ONE_DAY, 86400),
    ],
)
def test_timeframe_duration_is_exact(timeframe: CandleTimeframe, seconds: int) -> None:
    assert timeframe_duration(timeframe) == timedelta(seconds=seconds)


def test_normalized_candle_normalizes_uuid_and_requires_closed_aligned_utc_ohlc() -> None:
    instrument_id = "00000000-0000-0000-0000-000000000001"
    candle = NormalizedCandle(
        instrument_id=instrument_id,  # type: ignore[arg-type]
        timeframe=CandleTimeframe.ONE_HOUR,
        open_time=datetime(2026, 7, 25, 12, tzinfo=UTC),
        close_time=datetime(2026, 7, 25, 13, tzinfo=UTC),
        open=Decimal("100"), high=Decimal("110"), low=Decimal("90"), close=Decimal("105"),
        base_volume=Decimal("1"), quote_volume=None, trade_count=1,
        source_label="Synthetic candle provider", venue_label=None,
        received_at=datetime(2026, 7, 25, 13, tzinfo=UTC),
    )

    assert candle.close == Decimal("105")
    assert candle.instrument_id == uuid.UUID(instrument_id)


def test_candle_request_normalizes_instrument_uuid_at_boundary() -> None:
    instrument_id = "00000000-0000-0000-0000-000000000001"
    request = CandleRequest(
        instrument_id=instrument_id,  # type: ignore[arg-type]
        instrument_slug="btc-usdt",
        timeframe=CandleTimeframe.ONE_HOUR,
        from_time=datetime(2026, 7, 25, 12, tzinfo=UTC),
        to_time=datetime(2026, 7, 25, 13, tzinfo=UTC),
    )

    assert request.instrument_id == uuid.UUID(instrument_id)


@pytest.mark.parametrize(
    "open_time",
    [
        datetime(2026, 7, 25, 12, 1, tzinfo=UTC),
        datetime(2026, 7, 25, 12, tzinfo=UTC).replace(tzinfo=None),
    ],
)
def test_normalized_candle_rejects_misaligned_or_naive_open_time(open_time: datetime) -> None:
    with pytest.raises(ValueError):
        NormalizedCandle(
            instrument_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            timeframe=CandleTimeframe.ONE_HOUR,
            open_time=open_time, close_time=open_time + timedelta(hours=1),
            open=Decimal("100"), high=Decimal("110"), low=Decimal("90"), close=Decimal("105"),
            base_volume=None, quote_volume=None, trade_count=None,
            source_label="Synthetic candle provider", venue_label=None,
            received_at=datetime(2026, 7, 25, 13, tzinfo=UTC),
        )


def test_candle_time_helpers_calculate_utc_boundaries_and_gaps() -> None:
    timeframe = CandleTimeframe.ONE_HOUR
    timestamp = datetime(2026, 7, 25, 12, 34, 56, tzinfo=UTC)
    first = datetime(2026, 7, 25, 10, tzinfo=UTC)
    third = datetime(2026, 7, 25, 12, tzinfo=UTC)

    assert bootstrap_window(timeframe) == timedelta(days=180)
    assert align_open_time(timestamp, timeframe) == datetime(2026, 7, 25, 12, tzinfo=UTC)
    assert latest_closed_open_time(timestamp, timeframe) == datetime(2026, 7, 25, 11, tzinfo=UTC)
    assert incremental_from(third, timeframe) == first
    assert detect_gaps((third, first, first), timeframe) == (
        datetime(2026, 7, 25, 11, tzinfo=UTC),
    )


async def test_fake_historical_provider_returns_closed_candles_with_own_price_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 7, 25, 13, tzinfo=UTC)
    request = CandleRequest(
        instrument_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        instrument_slug="btc-usdt",
        timeframe=CandleTimeframe.ONE_HOUR,
        from_time=datetime(2026, 7, 25, 10, tzinfo=UTC),
        to_time=datetime(2026, 7, 25, 11, tzinfo=UTC),
    )
    monkeypatch.setitem(FakeQuoteProvider._PRICES, "btc-usdt", Decimal("1"))
    provider = FakeHistoricalCandleProvider(clock=lambda: now)

    candles = await provider.fetch_candles(request)

    assert [candle.open_time for candle in candles] == [
        datetime(2026, 7, 25, 10, tzinfo=UTC),
        datetime(2026, 7, 25, 11, tzinfo=UTC),
    ]
    assert candles[0].instrument_id == request.instrument_id
    assert candles[0].open == Decimal("59996.00")
    assert candles[0].close_time == candles[0].open_time + timedelta(hours=1)
    assert candles[0].received_at == now
