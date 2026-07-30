from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from decimal import Decimal
from typing import ClassVar, Protocol

from .candles import CandleRequest, NormalizedCandle, timeframe_duration
from .types import (
    DataStatus,
    DelayClass,
    MarketStatus,
    MarketType,
    NormalizedQuote,
    PriceType,
    QuoteRequest,
)

_PRICE_QUANTUM = Decimal("0.01")
_ANCHOR_WIDTH = 8


def _stable_sample(*parts: object, modulus: int) -> int:
    payload = ":".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8, person=b"pepe-demo").digest()
    return int.from_bytes(digest, "big") % modulus


def _synthetic_price(
    base_price: Decimal,
    *,
    instrument_slug: str,
    timeframe: str,
    candle_index: int,
) -> Decimal:
    """Return one request-independent point on a bounded deterministic demo path."""
    anchor_index, position = divmod(candle_index, _ANCHOR_WIDTH)
    left = _stable_sample(instrument_slug, timeframe, anchor_index, modulus=801) - 400
    right = _stable_sample(instrument_slug, timeframe, anchor_index + 1, modulus=801) - 400
    interpolated = Decimal(left * (_ANCHOR_WIDTH - position) + right * position) / Decimal(
        _ANCHOR_WIDTH,
    )
    micro_movement = _stable_sample(
        instrument_slug,
        timeframe,
        candle_index,
        "micro",
        modulus=17,
    ) - 8
    relative_offset = (interpolated + Decimal(micro_movement)) / Decimal("100000")
    return (base_price * (Decimal(1) + relative_offset)).quantize(_PRICE_QUANTUM)


class QuoteProvider(Protocol):
    async def fetch_quotes(
        self,
        requests: Iterable[QuoteRequest],
    ) -> tuple[NormalizedQuote, ...]: ...


class FakeQuoteProvider:
    """Development/test-only deterministic provider with no network transport."""

    _PRICES: ClassVar[dict[str, Decimal]] = {
        "btc-usdt": Decimal("60000.00"),
        "eth-usdt": Decimal("3000.00"),
        "xau-usd": Decimal("2300.00"),
    }

    def __init__(self, *, clock: Callable[[], datetime]) -> None:
        self._clock = clock

    async def fetch_quotes(self, requests: Iterable[QuoteRequest]) -> tuple[NormalizedQuote, ...]:
        now = self._clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        return tuple(self._quote_for(request, now) for request in requests)

    def _quote_for(self, request: QuoteRequest, now: datetime) -> NormalizedQuote:
        try:
            base_price = self._PRICES[request.instrument_slug]
        except KeyError as error:
            raise ValueError("unsupported fake instrument") from error
        price = _synthetic_price(
            base_price,
            instrument_slug=request.instrument_slug,
            timeframe="1m",
            candle_index=int(now.timestamp() // 60),
        )
        return NormalizedQuote(
            instrument_id=request.instrument_id,
            instrument_slug=request.instrument_slug,
            provider_key=request.provider_key,
            provider_mapping_id=request.provider_mapping_id,
            provider_instrument_id=request.provider_instrument_id,
            source_label="Synthetic test source",
            source_venue="Synthetic test venue",
            market_type=MarketType.SPOT,
            price_type=PriceType.LAST_TRADE,
            price=price,
            bid=None,
            ask=None,
            mid=None,
            open_24h=None,
            high_24h=None,
            low_24h=None,
            change_24h=None,
            change_percent_24h=None,
            base_volume_24h=None,
            quote_volume_24h=None,
            provider_timestamp=now,
            observed_at=now,
            received_at=now,
            data_delay_seconds=0,
            market_status=MarketStatus.OPEN,
            data_status=DataStatus.FRESH,
            delay_class=DelayClass.INDICATIVE,
            stale_after_seconds=60,
            hard_expire_after_seconds=300,
            mapping_version=request.mapping_version,
            schema_version=1,
            provider_event_id=f"fake:{request.instrument_slug}:{int(now.timestamp())}",
        )


class HistoricalCandleProvider(Protocol):
    async def fetch_candles(self, request: CandleRequest) -> tuple[NormalizedCandle, ...]: ...


class FakeHistoricalCandleProvider:
    """Deterministic provider-neutral closed-candle source for local development/tests."""

    _PRICES: ClassVar[dict[str, Decimal]] = {
        "btc-usdt": Decimal("60000.00"),
        "eth-usdt": Decimal("3000.00"),
        "xau-usd": Decimal("2300.00"),
    }

    def __init__(self, *, clock: Callable[[], datetime]) -> None:
        self._clock = clock

    async def fetch_candles(self, request: CandleRequest) -> tuple[NormalizedCandle, ...]:
        try:
            price = self._PRICES[request.instrument_slug]
        except KeyError as error:
            raise ValueError("unsupported fake instrument") from error
        received_at = self._clock()
        if received_at.tzinfo is None:
            received_at = received_at.replace(tzinfo=UTC)
        duration = timeframe_duration(request.timeframe)
        candles: list[NormalizedCandle] = []
        open_time = request.from_time
        timeframe_seconds = int(duration.total_seconds())
        while open_time <= request.to_time:
            candle_index = int(open_time.timestamp() // timeframe_seconds)
            opening = _synthetic_price(
                price,
                instrument_slug=request.instrument_slug,
                timeframe=request.timeframe.value,
                candle_index=candle_index - 1,
            )
            closing = _synthetic_price(
                price,
                instrument_slug=request.instrument_slug,
                timeframe=request.timeframe.value,
                candle_index=candle_index,
            )
            wick_units = Decimal(
                4 + _stable_sample(
                    request.instrument_slug,
                    request.timeframe.value,
                    candle_index,
                    "wick",
                    modulus=15,
                ),
            )
            wick = (price * wick_units / Decimal("200000")).quantize(_PRICE_QUANTUM)
            candles.append(
                NormalizedCandle(
                    instrument_id=request.instrument_id,
                    timeframe=request.timeframe,
                    open_time=open_time,
                    close_time=open_time + duration,
                    open=opening,
                    high=max(opening, closing) + wick,
                    low=min(opening, closing) - wick,
                    close=closing,
                    base_volume=Decimal("1"),
                    quote_volume=closing,
                    trade_count=1,
                    source_label="Synthetic historical candle source",
                    venue_label="Synthetic test venue",
                    received_at=max(received_at, open_time + duration),
                ),
            )
            open_time += duration
        return tuple(candles)
