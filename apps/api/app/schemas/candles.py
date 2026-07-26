from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pepe_quote_core import CandleTimeframe, decimal_to_string
from pydantic import BaseModel


def _required_decimal_to_string(value: Decimal) -> str:
    return format(value, "f")


class CandleResponse(BaseModel):
    open_time: datetime
    close_time: datetime
    open: str
    high: str
    low: str
    close: str
    base_volume: str | None
    quote_volume: str | None
    trade_count: int | None
    source_label: str
    venue_label: str | None
    received_at: datetime

    @classmethod
    def from_values(
        cls,
        *,
        open_time: datetime,
        close_time: datetime,
        open_price: Decimal,
        high: Decimal,
        low: Decimal,
        close: Decimal,
        base_volume: Decimal | None,
        quote_volume: Decimal | None,
        trade_count: int | None,
        source_label: str,
        venue_label: str | None,
        received_at: datetime,
    ) -> CandleResponse:
        return cls(
            open_time=open_time.astimezone(UTC),
            close_time=close_time.astimezone(UTC),
            open=_required_decimal_to_string(open_price),
            high=_required_decimal_to_string(high),
            low=_required_decimal_to_string(low),
            close=_required_decimal_to_string(close),
            base_volume=decimal_to_string(base_volume),
            quote_volume=decimal_to_string(quote_volume),
            trade_count=trade_count,
            source_label=source_label,
            venue_label=venue_label,
            received_at=received_at.astimezone(UTC),
        )


class CandlesResponse(BaseModel):
    timeframe: CandleTimeframe
    items: list[CandleResponse]
