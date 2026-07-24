from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class AssetClass(StrEnum):
    CRYPTO_SPOT = "crypto_spot"
    METAL_FX_SPOT = "metal_fx_spot"
    EQUITY_INDEX = "equity_index"
    CURRENCY_INDEX = "currency_index"
    GOVERNMENT_YIELD = "government_yield"


class MarketType(StrEnum):
    SPOT = "spot"
    REFERENCE_INDEX = "reference_index"
    YIELD_REFERENCE = "yield_reference"


class CalendarKind(StrEnum):
    ALWAYS_OPEN = "always_open"
    PROVIDER_SESSION = "provider_session"
    EXCHANGE = "exchange"
    REFERENCE_DATA = "reference_data"


_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_PRECISION = 12
_MAX_METADATA_VERSION = 2_147_483_647


@dataclass(frozen=True, slots=True)
class CanonicalInstrument:
    """Provider-independent validated instrument metadata for the catalog."""

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
    is_enabled: bool
    metadata_version: int

    def __post_init__(self) -> None:
        if not _SLUG_PATTERN.fullmatch(self.slug) or not 1 <= len(self.slug) <= 64:
            raise ValueError("slug must be lowercase kebab-case and at most 64 characters")
        if not 1 <= len(self.symbol) <= 32:
            raise ValueError("symbol must contain between 1 and 32 characters")
        if not 1 <= len(self.display_name) <= 128:
            raise ValueError("display_name must contain between 1 and 128 characters")
        self._validate_asset_code("base_asset", self.base_asset)
        self._validate_asset_code("quote_asset", self.quote_asset)
        self._validate_precision("price_precision", self.price_precision)
        if self.quantity_precision is not None:
            self._validate_precision("quantity_precision", self.quantity_precision)
        if not 1 <= self.metadata_version <= _MAX_METADATA_VERSION:
            raise ValueError("metadata_version must be positive and within the supported range")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("timezone must be a valid IANA timezone") from error
        valid_calendar = _IDENTIFIER_PATTERN.fullmatch(self.trading_calendar) is not None
        if not valid_calendar or not 1 <= len(self.trading_calendar) <= 64:
            raise ValueError("trading_calendar must be a safe kebab-case identifier")
        self._validate_market_semantics()

    @staticmethod
    def _validate_asset_code(name: str, value: str | None) -> None:
        if value is not None and (not value.isupper() or not value.isalnum() or len(value) > 16):
            raise ValueError(
                f"{name} must be an uppercase alphanumeric code of at most 16 characters",
            )

    @staticmethod
    def _validate_precision(name: str, value: int) -> None:
        if not 0 <= value <= _MAX_PRECISION:
            raise ValueError(f"{name} precision must be between 0 and {_MAX_PRECISION}")

    def _validate_market_semantics(self) -> None:
        if self.asset_class in {AssetClass.CRYPTO_SPOT, AssetClass.METAL_FX_SPOT}:
            if self.market_type is not MarketType.SPOT:
                raise ValueError("spot asset classes require spot market_type")
            if self.base_asset is None or self.quote_asset is None:
                raise ValueError("spot pairs require base_asset and quote_asset")
        elif self.asset_class in {AssetClass.EQUITY_INDEX, AssetClass.CURRENCY_INDEX}:
            if self.market_type is not MarketType.REFERENCE_INDEX:
                raise ValueError("index asset classes require reference_index market_type")
        elif (
            self.asset_class is AssetClass.GOVERNMENT_YIELD
            and self.market_type is not MarketType.YIELD_REFERENCE
        ):
            raise ValueError("government_yield requires yield_reference market_type")
