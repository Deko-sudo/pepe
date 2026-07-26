from __future__ import annotations

from datetime import datetime

from pepe_quote_core import CandleTimeframe, timeframe_duration
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.models.asset_instrument import AssetInstrument
from app.db.models.market_candle import MarketCandle
from app.schemas.candles import CandleResponse, CandlesResponse


class HistoricalCandleService:
    async def resolve(
        self,
        db: AsyncSession,
        *,
        slug: str,
        timeframe: CandleTimeframe,
        from_time: datetime | None,
        to_time: datetime | None,
        limit: int,
    ) -> CandlesResponse | None:
        instrument = await db.scalar(
            select(AssetInstrument).where(
                AssetInstrument.slug == slug, AssetInstrument.is_enabled.is_(True),
            ),
        )
        if instrument is None:
            return None
        from_time, to_time = self._bound_range(timeframe, from_time, to_time, limit)
        statement: Select[tuple[MarketCandle]] = select(MarketCandle).where(
            MarketCandle.instrument_id == instrument.id,
            MarketCandle.timeframe == timeframe.value,
        )
        if from_time is not None:
            statement = statement.where(MarketCandle.open_time >= from_time)
        if to_time is not None:
            statement = statement.where(MarketCandle.open_time < to_time)
        if from_time is None and to_time is None:
            latest = statement.order_by(MarketCandle.open_time.desc()).limit(limit).subquery()
            latest_candle = aliased(MarketCandle, latest)
            statement = select(latest_candle).order_by(latest_candle.open_time.asc())
        else:
            statement = statement.order_by(MarketCandle.open_time.asc()).limit(limit)
        rows = list((await db.scalars(statement)).all())
        return CandlesResponse(
            timeframe=timeframe,
            items=[
                CandleResponse.from_values(
                    open_time=row.open_time,
                    close_time=row.close_time,
                    open_price=row.open,
                    high=row.high,
                    low=row.low,
                    close=row.close,
                    base_volume=row.base_volume,
                    quote_volume=row.quote_volume,
                    trade_count=row.trade_count,
                    source_label=row.source_label,
                    venue_label=row.venue_label,
                    received_at=row.received_at,
                )
                for row in rows
            ],
        )

    @staticmethod
    def _bound_range(
        timeframe: CandleTimeframe,
        from_time: datetime | None,
        to_time: datetime | None,
        limit: int,
    ) -> tuple[datetime | None, datetime | None]:
        duration = timeframe_duration(timeframe)
        if from_time is not None and to_time is not None:
            if from_time >= to_time:
                raise ValueError("from must be before to")
            if (to_time - from_time) > duration * limit:
                raise ValueError("range exceeds limit")
        elif from_time is not None:
            to_time = from_time + duration * limit
        elif to_time is not None:
            from_time = to_time - duration * limit
        return from_time, to_time
