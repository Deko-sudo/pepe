from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pepe_quote_core import (
    DataStatus,
    DelayClass,
    MarketStatus,
    MarketType,
    PriceType,
    decimal_to_string,
)
from pydantic import BaseModel


class QuoteProvenanceResponse(BaseModel):
    source_label: str
    venue_label: str | None
    market_type: MarketType
    price_type: PriceType
    delay_class: DelayClass


class CurrentQuoteResponse(BaseModel):
    slug: str
    price: str
    bid: str | None
    ask: str | None
    mid: str | None
    open_24h: str | None
    high_24h: str | None
    low_24h: str | None
    change_24h: str | None
    change_percent_24h: str | None
    base_volume_24h: str | None
    quote_volume_24h: str | None
    market_status: MarketStatus
    data_status: DataStatus
    observed_at: datetime
    received_at: datetime
    age_seconds: int
    provenance: QuoteProvenanceResponse

    @classmethod
    def from_values(
        cls,
        *,
        slug: str,
        price: Decimal,
        bid: Decimal | None,
        ask: Decimal | None,
        mid: Decimal | None,
        open_24h: Decimal | None,
        high_24h: Decimal | None,
        low_24h: Decimal | None,
        change_24h: Decimal | None,
        change_percent_24h: Decimal | None,
        base_volume_24h: Decimal | None,
        quote_volume_24h: Decimal | None,
        market_status: MarketStatus,
        data_status: DataStatus,
        observed_at: datetime,
        received_at: datetime,
        age_seconds: int,
        market_type: MarketType,
        price_type: PriceType,
        delay_class: DelayClass,
        source_label: str,
        venue_label: str | None,
    ) -> CurrentQuoteResponse:
        return cls(
            slug=slug,
            price=decimal_to_string(price) or "0",
            bid=decimal_to_string(bid),
            ask=decimal_to_string(ask),
            mid=decimal_to_string(mid),
            open_24h=decimal_to_string(open_24h),
            high_24h=decimal_to_string(high_24h),
            low_24h=decimal_to_string(low_24h),
            change_24h=decimal_to_string(change_24h),
            change_percent_24h=decimal_to_string(change_percent_24h),
            base_volume_24h=decimal_to_string(base_volume_24h),
            quote_volume_24h=decimal_to_string(quote_volume_24h),
            market_status=market_status,
            data_status=data_status,
            observed_at=observed_at.astimezone(UTC),
            received_at=received_at.astimezone(UTC),
            age_seconds=age_seconds,
            provenance=QuoteProvenanceResponse(
                source_label=source_label,
                venue_label=venue_label,
                market_type=market_type,
                price_type=price_type,
                delay_class=delay_class,
            ),
        )


class CurrentQuoteBatchResponse(BaseModel):
    items: list[CurrentQuoteResponse]
    unavailable: list[str]
    not_found: list[str]
