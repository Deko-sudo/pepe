from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from pepe_quote_core import CandleTimeframe, NormalizedCandle, timeframe_duration


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


def test_normalized_candle_requires_closed_aligned_utc_ohlc() -> None:
    candle = NormalizedCandle(
        instrument_id="00000000-0000-0000-0000-000000000001",
        timeframe=CandleTimeframe.ONE_HOUR,
        open_time=datetime(2026, 7, 25, 12, tzinfo=UTC),
        close_time=datetime(2026, 7, 25, 13, tzinfo=UTC),
        open=Decimal("100"), high=Decimal("110"), low=Decimal("90"), close=Decimal("105"),
        base_volume=Decimal("1"), quote_volume=None, trade_count=1,
        source_label="Synthetic candle provider", venue_label=None,
        received_at=datetime(2026, 7, 25, 13, tzinfo=UTC),
    )

    assert candle.close == Decimal("105")


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
            instrument_id="00000000-0000-0000-0000-000000000001",
            timeframe=CandleTimeframe.ONE_HOUR,
            open_time=open_time, close_time=open_time + timedelta(hours=1),
            open=Decimal("100"), high=Decimal("110"), low=Decimal("90"), close=Decimal("105"),
            base_volume=None, quote_volume=None, trade_count=None,
            source_label="Synthetic candle provider", venue_label=None,
            received_at=datetime(2026, 7, 25, 13, tzinfo=UTC),
        )
