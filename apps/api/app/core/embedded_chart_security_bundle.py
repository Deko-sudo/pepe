from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import mkdtemp
from urllib.parse import urlsplit

from pepe_quote_core import MarketDataMode

from app.core.embedded_chart import EmbeddedChartProvider, canonical_wrapper_origin

EMBEDDED_CHART_SECURITY_BUNDLE_VERSION = 1
_SUPPORTED_ENVIRONMENTS = frozenset({"development", "test", "production"})
_PROVIDER = EmbeddedChartProvider.TRADINGVIEW_ISOLATED_WRAPPER
_PERMISSION_POLICY = (
    "camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=(), bluetooth=(), "
    "clipboard-read=(), clipboard-write=()"
)


@dataclass(frozen=True)
class EmbeddedChartSecurityBundle:
    digest: str
    environment: str
    enabled: bool
    provider: EmbeddedChartProvider
    parent_origin: str | None
    wrapper_origin: str | None


def _canonical_origin(value: object, *, environment: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty exact origin")
    if (
        value != value.strip()
        or "\\" in value
        or any(character.isspace() or ord(character) < 32 for character in value)
    ):
        raise ValueError(f"{field} must not contain whitespace or control characters")
    if "%" in value or "*" in value:
        raise ValueError(f"{field} must not contain ambiguous encoding or wildcards")
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError as error:
        raise ValueError(f"{field} has an invalid port") from error
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"{field} must be a bare HTTP(S) origin")
    if parsed.hostname.lower().endswith("tradingview.com"):
        raise ValueError(f"{field} must not be a provider origin")
    if field == "wrapper_origin":
        return canonical_wrapper_origin(value, environment=environment)
    port = (
        f":{parsed.port}"
        if parsed.port is not None
        and not (
            (parsed.scheme == "http" and parsed.port == 80)
            or (parsed.scheme == "https" and parsed.port == 443)
        )
        else ""
    )
    return f"{parsed.scheme}://{parsed.hostname.lower()}{port}"


def _blocked_state(manifest: dict[str, object]) -> EmbeddedChartSecurityBundle:
    raw_environment = manifest.get("environment")
    environment = raw_environment if isinstance(raw_environment, str) else "invalid"
    return EmbeddedChartSecurityBundle(
        digest="",
        environment=environment,
        enabled=False,
        provider=EmbeddedChartProvider.NONE,
        parent_origin=None,
        wrapper_origin=None,
    )


def validate_manifest(manifest: dict[str, object]) -> EmbeddedChartSecurityBundle:
    try:
        if manifest.get("version") != EMBEDDED_CHART_SECURITY_BUNDLE_VERSION:
            raise ValueError("unsupported embedded-chart security bundle version")
        environment = manifest.get("environment")
        if not isinstance(environment, str) or environment not in _SUPPORTED_ENVIRONMENTS:
            raise ValueError("unsupported embedded-chart environment")
        kill_switch = manifest.get("embedded_chart_kill_switch")
        if type(kill_switch) is not bool:
            raise ValueError("embedded_chart_kill_switch must be a boolean")
        provider = manifest.get("embedded_chart_provider")
        mode = manifest.get("market_data_mode")
        enabled = manifest.get("embedded_chart_enabled")
        if environment == "production" or kill_switch:
            return EmbeddedChartSecurityBundle(
                "", environment, False, EmbeddedChartProvider.NONE, None, None,
            )
        if not (
            environment in {"development", "test"}
            and mode == MarketDataMode.EMBEDDED.value
            and enabled is True
            and provider == _PROVIDER.value
        ):
            raise ValueError("embedded chart activation is not authorized")
        parent_origin = _canonical_origin(
            manifest.get("parent_origin"), environment=environment, field="parent_origin",
        )
        wrapper_origin = _canonical_origin(
            manifest.get("wrapper_origin"), environment=environment, field="wrapper_origin",
        )
        if parent_origin == wrapper_origin:
            raise ValueError("parent_origin and wrapper_origin must be separate origins")
        return EmbeddedChartSecurityBundle(
            "", environment, True, _PROVIDER, parent_origin, wrapper_origin,
        )
    except ValueError:
        return _blocked_state(manifest)


def _csp(bundle: EmbeddedChartSecurityBundle) -> tuple[str, str]:
    parent_frame_source = bundle.wrapper_origin if bundle.enabled else "'none'"
    parent = "; ".join(
        (
            "default-src 'self'",
            "base-uri 'none'",
            "object-src 'none'",
            "form-action 'none'",
            f"frame-src {parent_frame_source}",
            "script-src 'self'",
            "style-src 'self'",
            "connect-src 'self'",
            "img-src 'self'",
            "font-src 'none'",
            "worker-src 'none'",
            "media-src 'none'",
            "manifest-src 'self'",
        ),
    )
    wrapper_script_source = "'self' https://s3.tradingview.com" if bundle.enabled else "'self'"
    wrapper_frame_source = "https://s.tradingview.com" if bundle.enabled else "'none'"
    wrapper_ancestors = bundle.parent_origin if bundle.enabled else "'none'"
    wrapper = "; ".join(
        (
            "default-src 'none'",
            "base-uri 'none'",
            "object-src 'none'",
            "form-action 'none'",
            f"frame-ancestors {wrapper_ancestors}",
            f"script-src {wrapper_script_source}",
            "style-src 'self'",
            "img-src 'self'",
            f"frame-src {wrapper_frame_source}",
            "connect-src 'none'",
            "font-src 'none'",
            "media-src 'none'",
            "worker-src 'none'",
            "manifest-src 'none'",
        ),
    )
    return parent, wrapper


def _digest_input(bundle: EmbeddedChartSecurityBundle, parent_csp: str, wrapper_csp: str) -> bytes:
    return json.dumps({
        "enabled": bundle.enabled,
        "environment": bundle.environment,
        "parent_csp": parent_csp,
        "parent_origin": bundle.parent_origin,
        "provider": bundle.provider.value,
        "schema_version": EMBEDDED_CHART_SECURITY_BUNDLE_VERSION,
        "wrapper_csp": wrapper_csp,
        "wrapper_origin": bundle.wrapper_origin,
    }, sort_keys=True, separators=(",", ":")).encode()


def _headers(csp: str, digest: str) -> str:
    return (
        f'add_header Content-Security-Policy "{csp}" always;\n'
        'add_header Referrer-Policy "no-referrer" always;\n'
        'add_header X-Content-Type-Options "nosniff" always;\n'
        f'add_header Permissions-Policy "{_PERMISSION_POLICY}" always;\n'
        'add_header Cross-Origin-Resource-Policy "same-origin" always;\n'
        'add_header Cache-Control "no-store" always;\n'
        f'add_header X-Pepe-Embedded-Chart-Bundle "{digest}" always;\n'
    )


def compile_security_bundle(
    manifest: dict[str, object], output: Path,
) -> EmbeddedChartSecurityBundle:
    state = validate_manifest(manifest)
    parent_csp, wrapper_csp = _csp(state)
    digest = sha256(_digest_input(state, parent_csp, wrapper_csp)).hexdigest()
    bundle = EmbeddedChartSecurityBundle(
        digest,
        state.environment,
        state.enabled,
        state.provider,
        state.parent_origin,
        state.wrapper_origin,
    )
    api_settings = {
        "bundle_digest": digest,
        "embedded_chart_enabled": bundle.enabled,
        "embedded_chart_kill_switch": not bundle.enabled,
        "embedded_chart_provider": bundle.provider.value,
        "embedded_chart_wrapper_origin": bundle.wrapper_origin or "",
        "environment": bundle.environment,
        "market_data_mode": "embedded" if bundle.enabled else "unavailable",
        "parent_origin": bundle.parent_origin or "",
        "version": EMBEDDED_CHART_SECURITY_BUNDLE_VERSION,
    }
    metadata = {
        "bundle_digest": digest,
        "enabled": bundle.enabled,
        "environment": bundle.environment,
        "provider": bundle.provider.value,
        "schema_version": EMBEDDED_CHART_SECURITY_BUNDLE_VERSION,
    }
    temporary = Path(mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    # The wrapper uses the unprivileged nginx user and receives this directory
    # read-only through a shared volume.  mkdtemp defaults to 0700, which would
    # make a valid bundle unavailable to that consumer after publication.
    temporary.chmod(0o755)
    try:
        (temporary / "api-settings.json").write_text(
            json.dumps(api_settings, sort_keys=True, separators=(",", ":")) + "\n",
        )
        (temporary / "mini-app-security.conf").write_text(_headers(parent_csp, digest))
        wrapper_extra = (
            "location ~ ^/chart/(btc-usdt|eth-usdt|xau-usd)/(1m|5m|15m|1h|4h|1d)$ { return 503; }\n"
            if not bundle.enabled else ""
        )
        (temporary / "wrapper-security.conf").write_text(
            _headers(wrapper_csp, digest) + wrapper_extra,
        )
        (temporary / "bundle-metadata.json").write_text(
            json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n",
        )
        (temporary / "bundle.sha256").write_text(f"{digest}\n")
        backup = output.with_name(f".{output.name}.previous")
        if backup.exists():
            shutil.rmtree(backup)
        if output.exists():
            os.replace(output, backup)
        os.replace(temporary, output)
        if backup.exists():
            shutil.rmtree(backup)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return bundle


def load_security_bundle(directory: Path) -> EmbeddedChartSecurityBundle:
    required = (
        "api-settings.json",
        "mini-app-security.conf",
        "wrapper-security.conf",
        "bundle-metadata.json",
        "bundle.sha256",
    )
    if not directory.is_dir() or any(
        not (directory / filename).is_file() for filename in required
    ):
        raise ValueError("embedded-chart security bundle is missing required artifacts")
    api = json.loads((directory / "api-settings.json").read_text())
    metadata = json.loads((directory / "bundle-metadata.json").read_text())
    if not isinstance(api, dict) or not isinstance(metadata, dict):
        raise ValueError("embedded-chart security bundle artifacts must be JSON objects")
    digest = (directory / "bundle.sha256").read_text().strip()
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(char not in "0123456789abcdef" for char in digest)
    ):
        raise ValueError("embedded-chart security bundle digest is invalid")
    if api.get("bundle_digest") != digest or metadata.get("bundle_digest") != digest:
        raise ValueError("embedded-chart security bundle digest mismatch")
    manifest = {
        "version": api.get("version"),
        "environment": api.get("environment"),
        "market_data_mode": api.get("market_data_mode"),
        "embedded_chart_enabled": api.get("embedded_chart_enabled"),
        "embedded_chart_provider": api.get("embedded_chart_provider"),
        "embedded_chart_kill_switch": api.get("embedded_chart_kill_switch"),
        "parent_origin": api.get("parent_origin"),
        "wrapper_origin": api.get("embedded_chart_wrapper_origin"),
    }
    state = validate_manifest(manifest)
    parent_csp, wrapper_csp = _csp(state)
    expected = sha256(_digest_input(state, parent_csp, wrapper_csp)).hexdigest()
    if expected != digest:
        raise ValueError("embedded-chart security bundle contents do not match digest")
    header_digest = f'X-Pepe-Embedded-Chart-Bundle "{digest}"'
    if (
        header_digest not in (directory / "mini-app-security.conf").read_text()
        or header_digest not in (directory / "wrapper-security.conf").read_text()
    ):
        raise ValueError("embedded-chart security header digest mismatch")
    return EmbeddedChartSecurityBundle(
        digest,
        state.environment,
        state.enabled,
        state.provider,
        state.parent_origin,
        state.wrapper_origin,
    )
