from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from app.core.embedded_chart_security_bundle import (
    EMBEDDED_CHART_SECURITY_BUNDLE_VERSION,
    compile_security_bundle,
    load_security_bundle,
)


def active_manifest() -> dict[str, object]:
    return {
        "version": 1,
        "environment": "test",
        "market_data_mode": "embedded",
        "embedded_chart_enabled": True,
        "embedded_chart_provider": "tradingview_isolated_wrapper",
        "embedded_chart_kill_switch": False,
        "parent_origin": "http://127.0.0.1:4180",
        "wrapper_origin": "http://127.0.0.1:4182",
    }


def test_compiler_generates_one_deterministic_active_bundle(tmp_path: Path) -> None:
    output = tmp_path / "bundle"

    first = compile_security_bundle(active_manifest(), output)
    second = compile_security_bundle(active_manifest(), output)

    assert first.digest == second.digest
    assert first.enabled is True
    assert stat.S_IMODE(output.stat().st_mode) == 0o755
    assert (output / "api-settings.json").is_file()
    parent_security = (output / "mini-app-security.conf").read_text()
    wrapper_security = (output / "wrapper-security.conf").read_text()
    assert parent_security == (
        "add_header Content-Security-Policy \"default-src 'self'; base-uri 'none'; "
        "object-src 'none'; "
        "form-action 'none'; frame-src http://127.0.0.1:4182; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self'; font-src 'none'; worker-src 'none'; media-src 'none'; "
        "manifest-src 'self'\" always;\n"
        "add_header Referrer-Policy \"no-referrer\" always;\n"
        "add_header X-Content-Type-Options \"nosniff\" always;\n"
        "add_header Permissions-Policy \"camera=(), microphone=(), geolocation=(), payment=(), "
        "usb=(), serial=(), bluetooth=(), clipboard-read=(), clipboard-write=()\" always;\n"
        "add_header Cross-Origin-Resource-Policy \"same-origin\" always;\n"
        "add_header Cache-Control \"no-store\" always;\n"
        f"add_header X-Pepe-Embedded-Chart-Bundle \"{first.digest}\" always;\n"
    )
    assert "frame-ancestors http://127.0.0.1:4180" in wrapper_security
    assert "script-src 'self' https://s3.tradingview.com" in wrapper_security
    assert "frame-src https://s.tradingview.com" in wrapper_security
    assert "unsafe-eval" not in parent_security + wrapper_security
    assert "*" not in parent_security + wrapper_security
    assert json.loads((output / "bundle-metadata.json").read_text()) == {
        "bundle_digest": first.digest,
        "enabled": True,
        "environment": "test",
        "provider": "tradingview_isolated_wrapper",
        "schema_version": EMBEDDED_CHART_SECURITY_BUNDLE_VERSION,
    }
    assert (output / "bundle.sha256").read_text() == f"{first.digest}\n"


@pytest.mark.parametrize("value", [None, "true ", " True", "TRUE", "1", "yes", "false"])
def test_missing_or_malformed_kill_switch_fails_closed(value: object, tmp_path: Path) -> None:
    manifest = active_manifest()
    if value is None:
        manifest.pop("embedded_chart_kill_switch")
    else:
        manifest["embedded_chart_kill_switch"] = value

    bundle = compile_security_bundle(manifest, tmp_path / "bundle")

    assert bundle.enabled is False
    parent_security = (tmp_path / "bundle" / "mini-app-security.conf").read_text()
    wrapper_security = (tmp_path / "bundle" / "wrapper-security.conf").read_text()
    assert "frame-src 'none'" in parent_security
    assert "frame-ancestors 'none'" in wrapper_security
    assert "return 503" in wrapper_security


@pytest.mark.parametrize(
    "environment", ["production", "staging", "preview", "qa", "unknown", ""],
)
def test_unsupported_or_production_environment_fails_closed(
    environment: str, tmp_path: Path,
) -> None:
    manifest = active_manifest()
    manifest["environment"] = environment

    bundle = compile_security_bundle(manifest, tmp_path / "bundle")

    assert bundle.enabled is False


def test_same_origins_and_malformed_manifest_fail_closed_without_partial_publication(
    tmp_path: Path,
) -> None:
    output = tmp_path / "bundle"
    compile_security_bundle(active_manifest(), output)
    original_digest = (output / "bundle.sha256").read_text()
    invalid = active_manifest()
    invalid["wrapper_origin"] = invalid["parent_origin"]

    bundle = compile_security_bundle(invalid, output)

    assert bundle.enabled is False
    assert (output / "bundle.sha256").read_text() != original_digest
    assert load_security_bundle(output).enabled is False


def test_loaded_api_settings_refuse_digest_mismatch_and_missing_bundle(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing"):
        load_security_bundle(tmp_path / "missing")

    output = tmp_path / "bundle"
    compile_security_bundle(active_manifest(), output)
    (output / "bundle.sha256").write_text("0" * 64 + "\n")

    with pytest.raises(ValueError, match="digest"):
        load_security_bundle(output)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("parent_origin", "https://user:pass@example.test"),
        ("parent_origin", "https://example.test/path"),
        ("parent_origin", "https://example.test?query=yes"),
        ("parent_origin", "https://example.test#fragment"),
        ("parent_origin", "//example.test"),
        ("parent_origin", "https://example.test\\ambiguous"),
        ("wrapper_origin", "http://*.example.test"),
        ("wrapper_origin", "http://127.0.0.1:4182%2f"),
    ],
)
def test_ambiguous_origins_fail_closed(field: str, value: str, tmp_path: Path) -> None:
    manifest = active_manifest()
    manifest[field] = value

    bundle = compile_security_bundle(manifest, tmp_path / "bundle")

    assert bundle.enabled is False


def test_loader_rejects_non_object_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    compile_security_bundle(active_manifest(), output)
    (output / "api-settings.json").write_text("[]")

    with pytest.raises(ValueError, match="JSON objects"):
        load_security_bundle(output)
