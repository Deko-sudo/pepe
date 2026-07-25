from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from decimal import Decimal
from typing import ClassVar, Protocol

from .types import (
    DataStatus,
    DelayClass,
    MarketStatus,
    MarketType,
    NormalizedQuote,
    PriceType,
    QuoteRequest,
)


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
            price = self._PRICES[request.instrument_slug]
        except KeyError as error:
            raise ValueError("unsupported fake instrument") from error
        bid = price - Decimal("0.50")
        ask = price + Decimal("0.50")
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
            bid=bid,
            ask=ask,
            mid=(bid + ask) / Decimal("2"),
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
            delay_class=DelayClass.REALTIME,
            stale_after_seconds=60,
            hard_expire_after_seconds=300,
            mapping_version=request.mapping_version,
            schema_version=1,
            provider_event_id=f"fake:{request.instrument_slug}:{int(now.timestamp())}",
        )
