from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketCandle(Base):
    __tablename__ = "market_candles"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id", "timeframe", "open_time", name="uq_market_candles_identity",
        ),
        CheckConstraint("close_time > open_time", name="ck_market_candles_positive_interval"),
        CheckConstraint(
            "open > 0 AND high > 0 AND low > 0 AND close > 0",
            name="ck_market_candles_ohlc_positive",
        ),
        CheckConstraint(
            "high >= open AND high >= close AND high >= low", name="ck_market_candles_high_bounds",
        ),
        CheckConstraint("low <= open AND low <= close", name="ck_market_candles_low_bounds"),
        CheckConstraint(
            "base_volume IS NULL OR base_volume >= 0",
            name="ck_market_candles_base_volume_nonnegative",
        ),
        CheckConstraint(
            "quote_volume IS NULL OR quote_volume >= 0",
            name="ck_market_candles_quote_volume_nonnegative",
        ),
        CheckConstraint(
            "trade_count IS NULL OR trade_count >= 0",
            name="ck_market_candles_trade_count_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_instruments.id", ondelete="RESTRICT"), nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    base_volume: Mapped[Decimal | None] = mapped_column(Numeric(38, 18))
    quote_volume: Mapped[Decimal | None] = mapped_column(Numeric(38, 18))
    trade_count: Mapped[int | None] = mapped_column(Integer)
    source_label: Mapped[str] = mapped_column(String(128), nullable=False)
    venue_label: Mapped[str | None] = mapped_column(String(128))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )
