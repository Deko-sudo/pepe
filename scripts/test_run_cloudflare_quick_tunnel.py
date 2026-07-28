"""Regression tests for the Cloudflare quick tunnel environment persistence.

These tests guard the invariant that, while a public quick tunnel is active,
the public HTTPS origin stays in both the CSRF/CORS allowlists and secure
cookie settings survive any plain ``docker compose up`` (rebuild, restart, or
``make up``). The earlier regression was a CSRF 403: the tunnel-derived config
was only held in the tunnel script's process environment, so a mini-app rebuild
that cascade-recreated the API reverted it to localhost-only origins.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_cloudflare_quick_tunnel.py"


def _load_tunnel_module():
    spec = importlib.util.spec_from_file_location(
        "run_cloudflare_quick_tunnel", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_cloudflare_quick_tunnel"] = module
    spec.loader.exec_module(module)
    return module


def _tunnel_env(public_url: str) -> dict[str, str]:
    return {
        "CORS_ALLOWED_ORIGINS": f"{public_url},http://localhost:4000",
        "SESSION_ALLOWED_ORIGINS": f"{public_url},http://localhost:4000",
        "SESSION_COOKIE_SECURE": "true",
        "SESSION_COOKIE_SAME_SITE": "none",
        "SESSION_COOKIE_PARTITIONED": "true",
        "MINI_APP_URL": public_url,
        "MINI_APP_BUILD_ID": "abcd1234",
    }


def test_apply_tunnel_env_merges_public_origin_into_env(tmp_path: Path) -> None:
    tunnel = _load_tunnel_module()
    existing = (
        "APP_ENV=development\n"
        "TELEGRAM_BOT_TOKEN=secret-value\n"
        "MINI_APP_URL=http://localhost\n"
        "SESSION_ALLOWED_ORIGINS=http://localhost:4000\n"
    )
    (tmp_path / ".env").write_text(existing, encoding="utf-8")
    public_url = "https://enhancing-links-naturally-reaches.trycloudflare.com"

    tunnel.apply_tunnel_env(tmp_path, _tunnel_env(public_url))

    merged = tunnel._parse_env_file(tmp_path / ".env")
    assert public_url in merged["SESSION_ALLOWED_ORIGINS"]
    assert public_url in merged["CORS_ALLOWED_ORIGINS"]
    assert merged["SESSION_COOKIE_SECURE"] == "true"
    assert merged["SESSION_COOKIE_SAME_SITE"] == "none"
    assert merged["SESSION_COOKIE_PARTITIONED"] == "true"
    assert merged["MINI_APP_URL"] == public_url
    # Untouched keys must be preserved verbatim.
    assert merged["APP_ENV"] == "development"
    assert merged["TELEGRAM_BOT_TOKEN"] == "secret-value"


def test_apply_tunnel_env_backups_original_env(tmp_path: Path) -> None:
    tunnel = _load_tunnel_module()
    original = "TELEGRAM_BOT_TOKEN=secret-value\nAPP_ENV=development\n"
    (tmp_path / ".env").write_text(original, encoding="utf-8")

    tunnel.apply_tunnel_env(
        tmp_path, _tunnel_env("https://example.trycloudflare.com")
    )

    backup = tmp_path / ".env.tunnel-backup"
    assert backup.exists()
    assert backup.read_text(encoding="utf-8") == original


def test_restore_env_reverts_to_original_values(tmp_path: Path) -> None:
    tunnel = _load_tunnel_module()
    original = (
        "TELEGRAM_BOT_TOKEN=secret-value\n"
        "MINI_APP_URL=http://localhost\n"
        "SESSION_ALLOWED_ORIGINS=http://localhost:4000\n"
    )
    (tmp_path / ".env").write_text(original, encoding="utf-8")

    tunnel.apply_tunnel_env(
        tmp_path, _tunnel_env("https://example.trycloudflare.com")
    )
    tunnel.restore_env(tmp_path)

    restored = (tmp_path / ".env").read_text(encoding="utf-8")
    assert restored == original
    assert not (tmp_path / ".env.tunnel-backup").exists()


def test_restore_env_removes_injected_keys_when_no_backup(tmp_path: Path) -> None:
    tunnel = _load_tunnel_module()
    # No pre-existing .env, so apply_tunnel_env injects keys without a backup.
    tunnel.apply_tunnel_env(
        tmp_path, _tunnel_env("https://example.trycloudflare.com")
    )
    assert not (tmp_path / ".env.tunnel-backup").exists()

    tunnel.restore_env(tmp_path)

    merged = tunnel._parse_env_file(tmp_path / ".env")
    assert "MINI_APP_URL" not in merged
    assert "SESSION_ALLOWED_ORIGINS" not in merged
    assert "SESSION_COOKIE_SECURE" not in merged


def test_apply_then_plain_compose_resolves_public_origin(tmp_path: Path) -> None:
    """A plain ``${SESSION_ALLOWED_ORIGINS:-localhost}`` substitution must pick
    up the public origin after apply_tunnel_env, mirroring ``docker compose``
    variable substitution that reads ``.env``."""
    tunnel = _load_tunnel_module()
    public_url = "https://enhancing-links-naturally-reaches.trycloudflare.com"
    (tmp_path / ".env").write_text("", encoding="utf-8")

    tunnel.apply_tunnel_env(tmp_path, _tunnel_env(public_url))

    merged = tunnel._parse_env_file(tmp_path / ".env")
    # The compose default is localhost-only; after applying the tunnel config
    # the resolved value must contain the public origin (no localhost fallback).
    assert public_url in merged["SESSION_ALLOWED_ORIGINS"]
    assert merged["SESSION_ALLOWED_ORIGINS"].count("https://") == 1


def test_second_apply_does_not_overwrite_original_backup(tmp_path: Path) -> None:
    """A second tunnel start (or an orphaned prior process) must not replace the
    original ``.env`` backup with an already-tunnel-modified snapshot, otherwise
    restore_env would reinstate tunnel origins instead of the developer's values."""
    tunnel = _load_tunnel_module()
    original = (
        "TELEGRAM_BOT_TOKEN=secret-value\n"
        "MINI_APP_URL=http://localhost\n"
        "SESSION_ALLOWED_ORIGINS=http://localhost:4000\n"
    )
    (tmp_path / ".env").write_text(original, encoding="utf-8")

    first_url = "https://first.trycloudflare.com"
    second_url = "https://second.trycloudflare.com"
    tunnel.apply_tunnel_env(tmp_path, _tunnel_env(first_url))
    tunnel.apply_tunnel_env(tmp_path, _tunnel_env(second_url))

    # The backup must still hold the developer's original .env.
    backup = tmp_path / ".env.tunnel-backup"
    assert backup.read_text(encoding="utf-8") == original

    # And restoring must return the original values, not the first tunnel's.
    tunnel.restore_env(tmp_path)
    restored = (tmp_path / ".env").read_text(encoding="utf-8")
    assert restored == original
