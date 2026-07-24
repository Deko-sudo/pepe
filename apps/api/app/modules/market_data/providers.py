from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from app.modules.market_data.errors import InstrumentNotMapped


@dataclass(frozen=True, slots=True)
class ProviderIdentity:
    key: str
    display_name: str


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    supports_mapping_discovery: bool
    supports_availability_checks: bool
    supports_quotes: bool
    supports_candles: bool
    rate_limit_metadata_available: bool


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    is_available: bool
    checked_at: datetime | None
    detail: str | None


@dataclass(frozen=True, slots=True)
class InstrumentAvailability:
    instrument_id: uuid.UUID
    is_available: bool
    checked_at: datetime | None


@dataclass(frozen=True, slots=True)
class ProviderMapping:
    instrument_id: uuid.UUID
    provider_key: str
    provider_symbol: str
    provider_market: str
    priority: int
    is_enabled: bool
    mapping_version: int = 1


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    instrument_id: uuid.UUID
    provider_key: str
    provider_symbol: str
    provider_market: str
    priority: int


@runtime_checkable
class MarketDataProvider(Protocol):
    """Adapter boundary; concrete adapters are intentionally deferred past Stage 5."""

    async def get_identity(self) -> ProviderIdentity: ...

    async def get_capabilities(self) -> ProviderCapabilities: ...

    async def get_health(self) -> ProviderHealth: ...

    async def list_supported_mappings(self) -> tuple[ProviderMapping, ...]: ...

    async def check_availability(self, mapping: ProviderMapping) -> InstrumentAvailability: ...


def select_mapping(
    instrument_id: uuid.UUID,
    mappings: Iterable[ProviderMapping],
) -> ProviderSelection:
    enabled = [mapping for mapping in mappings if mapping.is_enabled]
    if not enabled:
        raise InstrumentNotMapped()
    selected = min(enabled, key=lambda mapping: (mapping.priority, mapping.provider_key))
    return ProviderSelection(
        instrument_id=selected.instrument_id,
        provider_key=selected.provider_key,
        provider_symbol=selected.provider_symbol,
        provider_market=selected.provider_market,
        priority=selected.priority,
    )
