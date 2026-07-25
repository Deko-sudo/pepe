from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum

_MAX_MAGNITUDE = Decimal("100000000000000000000")


class MarketType(StrEnum):
    SPOT = "spot"
    OTC_REFERENCE = "otc_reference"
    BROKER_QUOTE = "broker_quote"
    INDEX = "index"
    OTHER_APPROVED = "other_approved"


class PriceType(StrEnum):
    LAST_TRADE = "last_trade"
    BID = "bid"
    ASK = "ask"
    MIDPOINT = "midpoint"
    INDICATIVE = "indicative"
    REFERENCE = "reference"
    FIXING = "fixing"
    OTHER_APPROVED = "other_approved"


class MarketStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class DataStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    HARD_EXPIRED = "hard_expired"
    UNAVAILABLE = "unavailable"


class DelayClass(StrEnum):
    REALTIME = "realtime"
    DELAYED = "delayed"
    INDICATIVE = "indicative"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    stale_after_seconds: int
    hard_expire_after_seconds: int
    future_skew_seconds: int

    def __post_init__(self) -> None:
        if self.stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")
        if self.hard_expire_after_seconds <= self.stale_after_seconds:
            raise ValueError("hard_expire_after_seconds must exceed stale_after_seconds")
        if self.future_skew_seconds < 0:
            raise ValueError("future_skew_seconds must not be negative")


@dataclass(frozen=True, slots=True)
class QuoteRequest:
    instrument_id: uuid.UUID
    instrument_slug: str
    provider_key: str
    provider_mapping_id: uuid.UUID
    provider_instrument_id: str | None
    mapping_version: int

    def __post_init__(self) -> None:
        if not self.instrument_slug:
            raise ValueError("instrument_slug must not be empty")
        if not self.provider_key:
            raise ValueError("provider_key must not be empty")
        if self.mapping_version <= 0:
            raise ValueError("mapping_version must be positive")


@dataclass(frozen=True, slots=True)
class PublicProvenance:
    source_label: str
    venue_label: str | None
    market_type: MarketType
    price_type: PriceType
    delay_class: DelayClass


@dataclass(frozen=True, slots=True)
class NormalizedQuote:
    instrument_id: uuid.UUID
    instrument_slug: str
    provider_key: str
    provider_mapping_id: uuid.UUID
    provider_instrument_id: str | None
    source_venue: str | None
    market_type: MarketType
    price_type: PriceType
    price: Decimal
    bid: Decimal | None
    ask: Decimal | None
    mid: Decimal | None
    open_24h: Decimal | None
    high_24h: Decimal | None
    low_24h: Decimal | None
    change_24h: Decimal | None
    change_percent_24h: Decimal | None
    base_volume_24h: Decimal | None
    quote_volume_24h: Decimal | None
    provider_timestamp: datetime
    observed_at: datetime
    received_at: datetime
    data_delay_seconds: int
    market_status: MarketStatus
    data_status: DataStatus
    delay_class: DelayClass
    stale_after_seconds: int
    hard_expire_after_seconds: int
    mapping_version: int
    schema_version: int
    provider_event_id: str | None

    def __post_init__(self) -> None:
        _validate_positive("price", self.price)
        _validate_optional_positive("bid", self.bid)
        _validate_optional_positive("ask", self.ask)
        _validate_optional_positive("mid", self.mid)
        _validate_optional_magnitude("open_24h", self.open_24h)
        _validate_optional_magnitude("high_24h", self.high_24h)
        _validate_optional_magnitude("low_24h", self.low_24h)
        _validate_optional_magnitude("change_24h", self.change_24h)
        _validate_optional_magnitude("change_percent_24h", self.change_percent_24h)
        _validate_optional_non_negative("base_volume_24h", self.base_volume_24h)
        _validate_optional_non_negative("quote_volume_24h", self.quote_volume_24h)
        if self.bid is not None and self.ask is not None and self.bid > self.ask:
            raise ValueError("bid must not exceed ask")
        if self.mid is not None:
            bid = self.bid
            ask = self.ask
            if bid is None or ask is None:
                raise ValueError("mid requires bid and ask")
            if self.mid != (bid + ask) / Decimal("2"):
                raise ValueError("mid must equal the derived bid/ask midpoint")
        if self.low_24h is not None and self.high_24h is not None and self.low_24h > self.high_24h:
            raise ValueError("low_24h must not exceed high_24h")
        for name, value in (
            ("provider_timestamp", self.provider_timestamp),
            ("observed_at", self.observed_at),
            ("received_at", self.received_at),
        ):
            _validate_utc_timestamp(name, value)
        if self.provider_timestamp > self.received_at:
            raise ValueError("provider_timestamp must not exceed received_at")
        if self.observed_at > self.received_at:
            raise ValueError("observed_at must not exceed received_at")
        if self.data_delay_seconds < 0:
            raise ValueError("data_delay_seconds must not be negative")
        if self.stale_after_seconds <= 0 or (
            self.hard_expire_after_seconds <= self.stale_after_seconds
        ):
            raise ValueError("freshness thresholds are invalid")
        if self.mapping_version <= 0 or self.schema_version <= 0:
            raise ValueError("mapping_version and schema_version must be positive")

    @property
    def provenance(self) -> PublicProvenance:
        return PublicProvenance(
            source_label="Synthetic test source",
            venue_label=self.source_venue,
            market_type=self.market_type,
            price_type=self.price_type,
            delay_class=self.delay_class,
        )


def calculate_data_status(
    *,
    observed_at: datetime,
    now: datetime,
    policy: FreshnessPolicy,
) -> DataStatus:
    _validate_utc_timestamp("observed_at", observed_at)
    _validate_utc_timestamp("now", now)
    if observed_at > now + timedelta(seconds=policy.future_skew_seconds):
        raise ValueError("observed_at exceeds allowed future clock skew")
    age_seconds = max(0, int((now - observed_at).total_seconds()))
    if age_seconds >= policy.hard_expire_after_seconds:
        return DataStatus.HARD_EXPIRED
    if age_seconds >= policy.stale_after_seconds:
        return DataStatus.STALE
    return DataStatus.FRESH


def compare_quote_recency(candidate: NormalizedQuote, stored: NormalizedQuote) -> int:
    """Return positive when candidate wins deterministic latest-quote ordering."""
    candidate_key = (
        candidate.observed_at,
        candidate.mapping_version,
        candidate.provider_event_id or "",
        candidate.provider_key,
    )
    stored_key = (
        stored.observed_at,
        stored.mapping_version,
        stored.provider_event_id or "",
        stored.provider_key,
    )
    return (candidate_key > stored_key) - (candidate_key < stored_key)


def decimal_to_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def parse_decimal(value: object, *, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"{field} must be a decimal") from error
    if not parsed.is_finite():
        raise ValueError(f"{field} must be finite")
    if abs(parsed) > _MAX_MAGNITUDE:
        raise ValueError(f"{field} exceeds supported magnitude")
    return parsed


def _validate_utc_timestamp(name: str, value: datetime) -> None:
    if (
        value.tzinfo is None
        or value.utcoffset() is None
        or value.utcoffset() != UTC.utcoffset(value)
    ):
        raise ValueError(f"{name} must be timezone-aware UTC")


def _validate_positive(name: str, value: Decimal) -> None:
    _validate_magnitude(name, value)
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")


def _validate_optional_positive(name: str, value: Decimal | None) -> None:
    if value is not None:
        _validate_positive(name, value)


def _validate_optional_non_negative(name: str, value: Decimal | None) -> None:
    if value is not None:
        _validate_magnitude(name, value)
        if value < 0:
            raise ValueError(f"{name} must not be negative")


def _validate_optional_magnitude(name: str, value: Decimal | None) -> None:
    if value is not None:
        _validate_magnitude(name, value)


def _validate_magnitude(name: str, value: Decimal) -> None:
    if not value.is_finite() or abs(value) > _MAX_MAGNITUDE:
        raise ValueError(f"{name} must be finite and within the supported magnitude")
