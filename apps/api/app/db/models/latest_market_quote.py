from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LatestMarketQuote(Base):
    """One monotonic, durable latest quote for each canonical instrument."""

    __tablename__ = "latest_market_quotes"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_latest_quotes_price_positive"),
        CheckConstraint("bid IS NULL OR bid > 0", name="ck_latest_quotes_bid_positive"),
        CheckConstraint("ask IS NULL OR ask > 0", name="ck_latest_quotes_ask_positive"),
        CheckConstraint(
            "bid IS NULL OR ask IS NULL OR bid <= ask",
            name="ck_latest_quotes_bid_lte_ask",
        ),
        CheckConstraint(
            "base_volume_24h IS NULL OR base_volume_24h >= 0",
            name="ck_latest_quotes_base_volume_nonnegative",
        ),
        CheckConstraint(
            "quote_volume_24h IS NULL OR quote_volume_24h >= 0",
            name="ck_latest_quotes_quote_volume_nonnegative",
        ),
        CheckConstraint(
            "low_24h IS NULL OR high_24h IS NULL OR low_24h <= high_24h",
            name="ck_latest_quotes_low_lte_high",
        ),
        CheckConstraint("mapping_version > 0", name="ck_latest_quotes_mapping_version_positive"),
        CheckConstraint("schema_version > 0", name="ck_latest_quotes_schema_version_positive"),
        CheckConstraint("data_delay_seconds >= 0", name="ck_latest_quotes_data_delay_nonnegative"),
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_instruments.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    provider_mapping_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_instrument_mappings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_instrument_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_label: Mapped[str] = mapped_column(String(128), nullable=False)
    source_venue: Mapped[str | None] = mapped_column(String(128), nullable=True)
    market_type: Mapped[str] = mapped_column(String(32), nullable=False)
    price_type: Mapped[str] = mapped_column(String(32), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    bid: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    ask: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    mid: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    open_24h: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    high_24h: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    low_24h: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    change_24h: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    change_percent_24h: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    base_volume_24h: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    quote_volume_24h: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    provider_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    market_status: Mapped[str] = mapped_column(String(32), nullable=False)
    delay_class: Mapped[str] = mapped_column(String(32), nullable=False)
    mapping_version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_event_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
