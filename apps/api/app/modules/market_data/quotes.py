from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from pepe_quote_core import DataStatus, DelayClass, MarketStatus, MarketType, PriceType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.asset_instrument import AssetInstrument
from app.db.models.latest_market_quote import LatestMarketQuote
from app.modules.market_data.quote_cache import CurrentQuoteCache
from app.schemas.quotes import CurrentQuoteResponse


class QuoteCache(Protocol):
    async def get(self, instrument_id: uuid.UUID) -> CurrentQuoteResponse | None: ...

    async def set(self, instrument_id: uuid.UUID, quote: CurrentQuoteResponse) -> None: ...

    async def close(self) -> None: ...


@dataclass(frozen=True)
class CurrentQuoteResolution:
    quote: CurrentQuoteResponse | None
    not_found: bool


class CurrentQuoteService:
    """Resolve current quotes with a request-scoped best-effort cache adapter."""

    def __init__(self, *, cache: QuoteCache | None = None) -> None:
        self._cache = cache
        self._owns_cache = cache is None

    async def close(self) -> None:
        """Close only the cache this service created for the request."""
        if self._owns_cache and self._cache is not None:
            await self._cache.close()
            self._cache = None

    async def get_current_quote_by_slug(
        self,
        db: AsyncSession,
        slug: str,
        *,
        now: datetime | None = None,
    ) -> CurrentQuoteResponse | None:
        return (await self.resolve_current_quote_by_slug(db, slug, now=now)).quote

    async def resolve_current_quote_by_slug(
        self,
        db: AsyncSession,
        slug: str,
        *,
        now: datetime | None = None,
    ) -> CurrentQuoteResolution:
        instrument = await _get_enabled_instrument(db, slug)
        if instrument is None:
            return CurrentQuoteResolution(quote=None, not_found=True)
        current_time = now or datetime.now(UTC)
        if self._cache is None:
            self._cache = CurrentQuoteCache()
        cached = await self._cache.get(instrument.id)
        if cached is not None:
            return CurrentQuoteResolution(
                quote=_apply_freshness(cached, instrument.asset_class, current_time),
                not_found=False,
            )
        quote = await _get_durable_quote(db, instrument.id)
        if quote is None:
            return CurrentQuoteResolution(quote=None, not_found=False)
        response = _response_from_quote(instrument, quote, current_time)
        if response is not None:
            await self._cache.set(instrument.id, response)
        return CurrentQuoteResolution(quote=response, not_found=False)


async def get_current_quote_by_slug(
    db: AsyncSession,
    slug: str,
    *,
    now: datetime | None = None,
) -> CurrentQuoteResponse | None:
    service = CurrentQuoteService()
    try:
        return await service.get_current_quote_by_slug(db, slug, now=now)
    finally:
        await service.close()


async def _get_enabled_instrument(db: AsyncSession, slug: str) -> AssetInstrument | None:
    result = await db.execute(
        select(AssetInstrument).where(
            AssetInstrument.slug == slug,
            AssetInstrument.is_enabled.is_(True),
        ),
    )
    return result.scalar_one_or_none()


async def _get_durable_quote(
    db: AsyncSession,
    instrument_id: object,
) -> LatestMarketQuote | None:
    result = await db.execute(
        select(LatestMarketQuote).where(LatestMarketQuote.instrument_id == instrument_id),
    )
    return result.scalar_one_or_none()


def _response_from_quote(
    instrument: AssetInstrument,
    quote: LatestMarketQuote,
    now: datetime,
) -> CurrentQuoteResponse | None:
    stale_after, _ = settings.quote_freshness_for(instrument.asset_class)
    response = CurrentQuoteResponse.from_values(
        slug=instrument.slug,
        price=quote.price,
        bid=quote.bid,
        ask=quote.ask,
        mid=quote.mid,
        open_24h=quote.open_24h,
        high_24h=quote.high_24h,
        low_24h=quote.low_24h,
        change_24h=quote.change_24h,
        change_percent_24h=quote.change_percent_24h,
        base_volume_24h=quote.base_volume_24h,
        quote_volume_24h=quote.quote_volume_24h,
        market_status=MarketStatus(quote.market_status),
        data_status=DataStatus.FRESH,
        observed_at=quote.observed_at,
        received_at=quote.received_at,
        age_seconds=0,
        market_type=MarketType(quote.market_type),
        price_type=PriceType(quote.price_type),
        delay_class=DelayClass(quote.delay_class),
        source_label=quote.source_label,
        venue_label=quote.source_venue,
        stale_after_seconds=stale_after,
    )
    return _apply_freshness(response, instrument.asset_class, now)


def _apply_freshness(
    quote: CurrentQuoteResponse,
    asset_class: str,
    now: datetime,
) -> CurrentQuoteResponse | None:
    age_seconds = max(0, int((now - quote.observed_at).total_seconds()))
    stale_after, hard_expire_after = settings.quote_freshness_for(asset_class)
    if age_seconds >= hard_expire_after:
        return None
    data_status = DataStatus.STALE if age_seconds >= stale_after else DataStatus.FRESH
    return quote.model_copy(
        update={
            "age_seconds": age_seconds,
            "data_status": data_status,
            "stale_after_seconds": stale_after,
        },
    )
