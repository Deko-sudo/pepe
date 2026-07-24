from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    SmallInteger,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AssetInstrument(Base):
    __tablename__ = "asset_instruments"
    __table_args__ = (
        CheckConstraint(
            "asset_class IN "
            "('crypto_spot', 'metal_fx_spot', 'equity_index', "
            "'currency_index', 'government_yield')",
            name="ck_asset_instruments_asset_class",
        ),
        CheckConstraint(
            "market_type IN ('spot', 'reference_index', 'yield_reference')",
            name="ck_asset_instruments_market_type",
        ),
        CheckConstraint(
            "calendar_kind IN ('always_open', 'provider_session', 'exchange', 'reference_data')",
            name="ck_asset_instruments_calendar_kind",
        ),
        CheckConstraint(
            "price_precision >= 0 AND price_precision <= 12",
            name="ck_asset_instruments_price_precision",
        ),
        CheckConstraint(
            "quantity_precision IS NULL OR (quantity_precision >= 0 AND quantity_precision <= 12)",
            name="ck_asset_instruments_quantity_precision",
        ),
        CheckConstraint(
            "metadata_version > 0",
            name="ck_asset_instruments_metadata_version_positive",
        ),
        Index("ix_asset_instruments_enabled_slug", "is_enabled", "slug"),
        Index("ix_asset_instruments_enabled_class_slug", "is_enabled", "asset_class", "slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(32), nullable=False)
    market_type: Mapped[str] = mapped_column(String(32), nullable=False)
    base_asset: Mapped[str | None] = mapped_column(String(16), nullable=True)
    quote_asset: Mapped[str | None] = mapped_column(String(16), nullable=True)
    price_precision: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    quantity_precision: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    calendar_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    trading_calendar: Mapped[str] = mapped_column(String(64), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    metadata_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
