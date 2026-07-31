import re
from enum import StrEnum
from ipaddress import ip_address
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, model_validator

EMBEDDED_CHART_CONTRACT_VERSION: Literal[1] = 1
CanonicalMarketSlug = Literal["btc-usdt", "eth-usdt", "xau-usd"]
CanonicalTimeframe = Literal["1m", "5m", "15m", "1h", "4h", "1d"]
_DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_BROWSER_IPV4_COMPONENT = re.compile(r"(?:0x[0-9a-f]+|0[0-7]*|[0-9]+)$", re.IGNORECASE)


class EmbeddedChartProvider(StrEnum):
    NONE = "none"
    TRADINGVIEW_ISOLATED_WRAPPER = "tradingview_isolated_wrapper"


def _valid_dns_hostname(hostname: str) -> bool:
    return (
        1 <= len(hostname) <= 253
        and hostname not in {"localhost", "metadata.google.internal"}
        and all(_DNS_LABEL.fullmatch(label) for label in hostname.split("."))
    )


def _looks_like_browser_ipv4(hostname: str) -> bool:
    """Identify legacy browser IPv4 spellings without resolving a host."""
    components = hostname.split(".")
    return 1 <= len(components) <= 4 and all(
        _BROWSER_IPV4_COMPONENT.fullmatch(component) for component in components
    )


def canonical_wrapper_origin(value: str, *, environment: str) -> str:
    """Validate a navigation origin without resolution or network access."""
    if not value or any(character.isspace() or ord(character) < 32 for character in value):
        raise ValueError("embedded_chart_wrapper_origin must be a non-empty bare origin")
    if "\\" in value or "%" in value:
        raise ValueError("embedded_chart_wrapper_origin must not contain ambiguous encoding")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise ValueError("embedded_chart_wrapper_origin has an invalid port") from error
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("embedded_chart_wrapper_origin must be a bare HTTP(S) origin")
    hostname = parsed.hostname.lower().rstrip(".")
    if not hostname or any(ord(character) > 127 for character in hostname):
        raise ValueError("embedded_chart_wrapper_origin hostname is not allowed")
    try:
        address = ip_address(hostname)
    except ValueError:
        address = None
    scheme = parsed.scheme.lower()
    if scheme == "http":
        if environment not in {"development", "test"} or hostname != "127.0.0.1":
            raise ValueError(
                "embedded_chart_wrapper_origin permits HTTP only for "
                "127.0.0.1 in development or test",
            )
    elif address is not None or _looks_like_browser_ipv4(hostname):
        raise ValueError("embedded_chart_wrapper_origin host is not allowed")
    if address is None and not _valid_dns_hostname(hostname):
        raise ValueError("embedded_chart_wrapper_origin hostname is not allowed")
    normalized_port = None if (scheme, port) in {("http", 80), ("https", 443)} else port
    authority = hostname if normalized_port is None else f"{hostname}:{normalized_port}"
    return urlunsplit((scheme, authority, "", "", ""))


def canonical_wrapper_path(slug: CanonicalMarketSlug, timeframe: CanonicalTimeframe) -> str:
    return f"/chart/{slug}/{timeframe}"


class EmbeddedChartConfigurationResponse(BaseModel):
    version: Literal[1] = EMBEDDED_CHART_CONTRACT_VERSION
    mode: Literal["embedded"] = "embedded"
    provider: EmbeddedChartProvider = EmbeddedChartProvider.TRADINGVIEW_ISOLATED_WRAPPER
    asset: CanonicalMarketSlug
    timeframe: CanonicalTimeframe
    wrapper_origin: str
    wrapper_path: str
    wrapper_url: str

    @model_validator(mode="after")
    def validate_invariants(self) -> "EmbeddedChartConfigurationResponse":
        if self.provider is not EmbeddedChartProvider.TRADINGVIEW_ISOLATED_WRAPPER:
            raise ValueError("wrapper configuration provider must be tradingview_isolated_wrapper")
        expected_path = canonical_wrapper_path(self.asset, self.timeframe)
        origin = urlsplit(self.wrapper_origin)
        url = urlsplit(self.wrapper_url)
        if (
            self.wrapper_path != expected_path
            or url.scheme != origin.scheme
            or url.netloc != origin.netloc
            or url.path != expected_path
            or url.query
            or url.fragment
            or url.username is not None
            or url.password is not None
        ):
            raise ValueError("wrapper configuration URL must be a canonical wrapper route")
        return self


def wrapper_configuration(
    *,
    origin: str,
    slug: CanonicalMarketSlug,
    timeframe: CanonicalTimeframe,
) -> EmbeddedChartConfigurationResponse:
    path = canonical_wrapper_path(slug, timeframe)
    parsed = urlsplit(origin)
    url = urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
    return EmbeddedChartConfigurationResponse(
        asset=slug,
        timeframe=timeframe,
        wrapper_origin=origin,
        wrapper_path=path,
        wrapper_url=url,
    )
