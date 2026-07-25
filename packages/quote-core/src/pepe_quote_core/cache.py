"""Strict versioned JSON codec for cached current-quote API responses."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Final

from .types import DataStatus, DelayClass, MarketStatus, MarketType, PriceType, PublicProvenance

_CACHE_SCHEMA_VERSION: Final = 1
_MAX_DECIMAL_MAGNITUDE: Final = Decimal("100000000000000000000")
_QUOTE_FIELDS: Final = frozenset(
    {
        "slug",
        "price",
        "bid",
        "ask",
        "mid",
        "open_24h",
        "high_24h",
        "low_24h",
        "change_24h",
        "change_percent_24h",
        "base_volume_24h",
        "quote_volume_24h",
        "market_status",
        "data_status",
        "observed_at",
        "received_at",
        "age_seconds",
        "provenance",
    },
)
_PROVENANCE_FIELDS: Final = frozenset(
    {"source_label", "venue_label", "market_type", "price_type", "delay_class"},
)


class CachePayloadError(ValueError):
    """Raised when a current-quote cache payload is invalid or unsupported."""


@dataclass(frozen=True, slots=True)
class CurrentQuoteCacheEntry:
    """The cache representation of the public ``CurrentQuoteResponse`` wire model."""

    slug: str
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
    market_status: MarketStatus
    data_status: DataStatus
    observed_at: datetime
    received_at: datetime
    age_seconds: int
    provenance: PublicProvenance


def encode_current_quote_cache(entry: CurrentQuoteCacheEntry) -> str:
    """Encode an entry using the version-1 public current-quote wire shape."""
    return json.dumps(
        {"schema_version": _CACHE_SCHEMA_VERSION, "quote": _quote_to_wire(entry)},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def decode_current_quote_cache(payload: str | bytes) -> CurrentQuoteCacheEntry:
    """Decode a strictly-shaped version-1 current-quote cache payload.

    Every invalid input is reported as :class:`CachePayloadError`, never as a
    JSON, decimal, timestamp, or enum implementation exception.
    """
    try:
        data = _exact_object(_load_payload(payload), {"schema_version", "quote"}, "payload")
        if data["schema_version"] != _CACHE_SCHEMA_VERSION:
            raise CachePayloadError("unsupported cache schema version")

        quote = _exact_object(data["quote"], _QUOTE_FIELDS, "quote")
        provenance = _exact_object(quote["provenance"], _PROVENANCE_FIELDS, "provenance")

        return CurrentQuoteCacheEntry(
            slug=_text(quote["slug"], "slug"),
            price=_decimal(quote["price"], "price"),
            bid=_optional_decimal(quote["bid"], "bid"),
            ask=_optional_decimal(quote["ask"], "ask"),
            mid=_optional_decimal(quote["mid"], "mid"),
            open_24h=_optional_decimal(quote["open_24h"], "open_24h"),
            high_24h=_optional_decimal(quote["high_24h"], "high_24h"),
            low_24h=_optional_decimal(quote["low_24h"], "low_24h"),
            change_24h=_optional_decimal(quote["change_24h"], "change_24h"),
            change_percent_24h=_optional_decimal(
                quote["change_percent_24h"], "change_percent_24h",
            ),
            base_volume_24h=_optional_decimal(quote["base_volume_24h"], "base_volume_24h"),
            quote_volume_24h=_optional_decimal(quote["quote_volume_24h"], "quote_volume_24h"),
            market_status=_enum(quote["market_status"], MarketStatus, "market_status"),
            data_status=_enum(quote["data_status"], DataStatus, "data_status"),
            observed_at=_timestamp(quote["observed_at"], "observed_at"),
            received_at=_timestamp(quote["received_at"], "received_at"),
            age_seconds=_non_negative_integer(quote["age_seconds"], "age_seconds"),
            provenance=PublicProvenance(
                source_label=_text(provenance["source_label"], "source_label"),
                venue_label=_optional_text(provenance["venue_label"], "venue_label"),
                market_type=_enum(provenance["market_type"], MarketType, "market_type"),
                price_type=_enum(provenance["price_type"], PriceType, "price_type"),
                delay_class=_enum(provenance["delay_class"], DelayClass, "delay_class"),
            ),
        )
    except CachePayloadError:
        raise
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise CachePayloadError("payload contains invalid values") from error


def _load_payload(payload: str | bytes) -> object:
    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError as error:
            raise CachePayloadError("payload is not UTF-8") from error
    if not isinstance(payload, str):
        raise CachePayloadError("payload must be str or bytes")
    try:
        return json.loads(
            payload,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, RecursionError) as error:
        raise CachePayloadError("payload is not valid JSON") from error


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CachePayloadError("payload contains duplicate object keys")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> object:
    raise CachePayloadError(f"invalid JSON constant {value!r}")


def _exact_object(
    value: object, fields: frozenset[str] | set[str], name: str,
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != fields:
        raise CachePayloadError(f"{name} shape is invalid")
    return value


def _quote_to_wire(entry: CurrentQuoteCacheEntry) -> dict[str, object]:
    return {
        "slug": entry.slug,
        "price": _decimal_wire(entry.price),
        "bid": _decimal_wire(entry.bid),
        "ask": _decimal_wire(entry.ask),
        "mid": _decimal_wire(entry.mid),
        "open_24h": _decimal_wire(entry.open_24h),
        "high_24h": _decimal_wire(entry.high_24h),
        "low_24h": _decimal_wire(entry.low_24h),
        "change_24h": _decimal_wire(entry.change_24h),
        "change_percent_24h": _decimal_wire(entry.change_percent_24h),
        "base_volume_24h": _decimal_wire(entry.base_volume_24h),
        "quote_volume_24h": _decimal_wire(entry.quote_volume_24h),
        "market_status": entry.market_status,
        "data_status": entry.data_status,
        "observed_at": entry.observed_at.isoformat(),
        "received_at": entry.received_at.isoformat(),
        "age_seconds": entry.age_seconds,
        "provenance": {
            "source_label": entry.provenance.source_label,
            "venue_label": entry.provenance.venue_label,
            "market_type": entry.provenance.market_type,
            "price_type": entry.provenance.price_type,
            "delay_class": entry.provenance.delay_class,
        },
    }


def _decimal_wire(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CachePayloadError(f"{field} is invalid")
    return value


def _optional_text(value: object, field: str) -> str | None:
    return None if value is None else _text(value, field)


def _decimal(value: object, field: str) -> Decimal:
    if not isinstance(value, str):
        raise CachePayloadError(f"{field} is invalid")
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise CachePayloadError(f"{field} is invalid") from error
    if not parsed.is_finite() or abs(parsed) > _MAX_DECIMAL_MAGNITUDE:
        raise CachePayloadError(f"{field} is invalid")
    return parsed


def _optional_decimal(value: object, field: str) -> Decimal | None:
    return None if value is None else _decimal(value, field)


def _non_negative_integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CachePayloadError(f"{field} is invalid")
    return value


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise CachePayloadError(f"{field} is invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise CachePayloadError(f"{field} is invalid") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CachePayloadError(f"{field} is invalid")
    return parsed


def _enum[EnumT: StrEnum](value: object, enum_type: type[EnumT], field: str) -> EnumT:
    if not isinstance(value, str):
        raise CachePayloadError(f"{field} is invalid")
    try:
        return enum_type(value)
    except ValueError as error:
        raise CachePayloadError(f"{field} is invalid") from error
