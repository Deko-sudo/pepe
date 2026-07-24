from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from app.modules.market_data.domain import AssetClass, CalendarKind, MarketType


class AssetCatalogItem(BaseModel):
    id: uuid.UUID
    slug: str
    symbol: str
    display_name: str
    asset_class: AssetClass
    market_type: MarketType
    base_asset: str | None
    quote_asset: str | None
    price_precision: int
    quantity_precision: int | None
    timezone: str
    calendar_kind: CalendarKind
    trading_calendar: str
    metadata_version: int
    is_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class AssetCatalogPage(BaseModel):
    items: list[AssetCatalogItem]
    next_cursor: str | None
