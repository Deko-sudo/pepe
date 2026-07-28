#!/usr/bin/env python3
"""Run a Cloudflare Quick Tunnel and configure the Telegram bot for its URL."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import selectors
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import BinaryIO

QUICK_TUNNEL_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
BUILD_ID = re.compile(r"^[a-zA-Z0-9._-]{1,32}$")
DEFAULT_ORIGIN = "http://localhost:4000"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_LOCAL_ORIGINS = (
    "http://localhost:3000,http://localhost:4000,http://localhost:8080"
)
ENV_FILE = ".env"
ENV_BACKUP = ".env.tunnel-backup"
TUNNEL_ENV_KEYS = (
    "CORS_ALLOWED_ORIGINS",
    "SESSION_ALLOWED_ORIGINS",
    "SESSION_COOKIE_SECURE",
    "SESSION_COOKIE_SAME_SITE",
    "SESSION_COOKIE_PARTITIONED",
    "MINI_APP_URL",
    "MINI_APP_BUILD_ID",
)


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value
    return values


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    lines = [f"{key}={values[key]}" for key in values]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_tunnel_env(repo_root: Path, environment: dict[str, str]) -> None:
    """Merge tunnel-derived config into ``.env`` so every ``docker compose``
    invocation (rebuild, restart, ``make up``) keeps the public origin in the
    CSRF/CORS allowlists and secure cookie settings while the tunnel is active.

    Compose auto-loads ``.env`` for ``${VAR:-default}`` substitution, so writing
    here is the only way a plain ``make up`` (or a mini-app rebuild that
    cascade-recreates the API) preserves the public origin. Without it the API
    reverts to localhost-only origins and the CSRF origin check rejects the
    tunnel origin with HTTP 403.

    The original ``.env`` is backed up and restored on tunnel exit so stopping
    the tunnel cleanly reverts to safe localhost defaults. Only the
    tunnel-controlled keys are touched; all other values (including
    ``TELEGRAM_BOT_TOKEN``) are preserved verbatim.
    """
    env_path = repo_root / ENV_FILE
    backup_path = repo_root / ENV_BACKUP
    if env_path.exists():
        backup_path.write_bytes(env_path.read_bytes())
    values = _parse_env_file(env_path)
    for key in TUNNEL_ENV_KEYS:
        if key in environment:
            values[key] = environment[key]
    _write_env_file(env_path, values)


def restore_env(repo_root: Path) -> None:
    """Restore the original ``.env`` captured before the tunnel applied its config."""
    env_path = repo_root / ENV_FILE
    backup_path = repo_root / ENV_BACKUP
    if backup_path.exists():
        env_path.write_bytes(backup_path.read_bytes())
        backup_path.unlink()
    else:
        # No backup means .env never existed before the tunnel; remove the keys
        # we may have injected so a localhost-only stack stays the default.
        values = _parse_env_file(env_path)
        changed = False
        for key in TUNNEL_ENV_KEYS:
            if key in values:
                del values[key]
                changed = True
        if changed:
            _write_env_file(env_path, values)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Start a random Cloudflare Quick Tunnel and recreate the Telegram "
            "bot with the generated Mini App URL."
        )
    )
    parser.add_argument(
        "--origin",
        default=os.environ.get("CLOUDFLARE_TUNNEL_ORIGIN", DEFAULT_ORIGIN),
        help=f"Local origin for cloudflared (default: {DEFAULT_ORIGIN})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Seconds to wait for the public URL (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    return parser.parse_args()


def stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def drain_stream(stream: BinaryIO) -> None:
    read = stream.read
    while chunk := read(4096):
        print(chunk.decode(errors="replace"), end="", file=sys.stderr, flush=True)


def resolve_build_id(repo_root: Path) -> str:
    configured = os.environ.get("MINI_APP_BUILD_ID", "").strip()
    if configured:
        if not BUILD_ID.fullmatch(configured):
            raise ValueError("MINI_APP_BUILD_ID must be a short safe identifier")
        return configured

    head = subprocess.check_output(
        ["git", "rev-parse", "--short=8", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()
    diff = subprocess.check_output(
        [
            "git",
            "diff",
            "--binary",
            "HEAD",
            "--",
            "apps/mini-app",
            "apps/api",
            "apps/bot",
        ],
        cwd=repo_root,
    )
    return head if not diff else f"{head}-{hashlib.sha256(diff).hexdigest()[:8]}"


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    tunnel = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", args.origin],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
    )

    def handle_signal(_signum: int, _frame: object) -> None:
        stop_process(tunnel)
        raise SystemExit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    public_url: str | None = None
    deadline = time.monotonic() + args.timeout
    assert tunnel.stdout is not None
    output_buffer = ""
    os.set_blocking(tunnel.stdout.fileno(), False)
    selector = selectors.DefaultSelector()
    selector.register(tunnel.stdout, selectors.EVENT_READ)

    while time.monotonic() < deadline:
        if tunnel.poll() is not None:
            output = tunnel.stdout.read().decode(errors="replace").strip()
            print(output, file=sys.stderr)
            print(
                "cloudflared exited before generating a Quick Tunnel URL",
                file=sys.stderr,
            )
            return 1

        events = selector.select(timeout=min(0.5, max(0, deadline - time.monotonic())))
        for _key, _ in events:
            chunk = os.read(tunnel.stdout.fileno(), 4096).decode(errors="replace")
            output_buffer += chunk
            lines = output_buffer.splitlines(keepends=True)
            output_buffer = (
                lines.pop() if lines and not lines[-1].endswith("\n") else ""
            )
            for line in lines:
                match = QUICK_TUNNEL_URL.search(line)
                if match:
                    public_url = match.group(0)
                    break
            if public_url is not None:
                break
        if public_url is not None:
            break

    if public_url is None:
        stop_process(tunnel)
        print(
            f"Timed out after {args.timeout:g}s waiting for a Cloudflare Quick Tunnel URL",
            file=sys.stderr,
        )
        return 1

    selector.unregister(tunnel.stdout)
    selector.close()
    os.set_blocking(tunnel.stdout.fileno(), True)
    threading.Thread(
        target=drain_stream,
        args=(tunnel.stdout,),
        daemon=True,
        name="cloudflared-output-drainer",
    ).start()

    try:
        print(f"Cloudflare Quick Tunnel: {public_url}")
        compose_environment = os.environ.copy()
        local_origins = compose_environment.get(
            "CLOUDFLARE_ALLOWED_LOCAL_ORIGINS",
            DEFAULT_LOCAL_ORIGINS,
        )
        allowed_origins = ",".join(
            origin for origin in (public_url, local_origins) if origin
        )
        compose_environment["CORS_ALLOWED_ORIGINS"] = allowed_origins
        compose_environment["SESSION_ALLOWED_ORIGINS"] = allowed_origins
        compose_environment["SESSION_COOKIE_SECURE"] = "true"
        compose_environment["SESSION_COOKIE_SAME_SITE"] = "none"
        compose_environment["SESSION_COOKIE_PARTITIONED"] = "true"
        compose_environment["MINI_APP_URL"] = public_url
        compose_environment["MINI_APP_BUILD_ID"] = resolve_build_id(repo_root)

        apply_tunnel_env(repo_root, compose_environment)

        print("Building and starting the versioned Mini App service...")
        subprocess.run(
            ["docker", "compose", "up", "-d", "--build", "mini-app"],
            cwd=repo_root,
            env=compose_environment,
            check=True,
        )

        print("Recreating the API with the generated HTTPS origin...")
        subprocess.run(
            ["docker", "compose", "up", "-d", "--no-deps", "--force-recreate", "api"],
            cwd=repo_root,
            env=compose_environment,
            check=True,
        )
        print("Recreating the Telegram bot with the generated Mini App URL...")
        subprocess.run(
            ["docker", "compose", "up", "-d", "--no-deps", "--force-recreate", "bot"],
            cwd=repo_root,
            env=compose_environment,
            check=True,
        )
        subprocess.run(["docker", "compose", "ps", "api"], cwd=repo_root, check=True)
        subprocess.run(["docker", "compose", "ps", "bot"], cwd=repo_root, check=True)
        print("Send /start to the bot to receive a button with the new URL.")
        print("Keep this process running; stopping it invalidates the public URL.")
        return tunnel.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        restore_env(repo_root)
        stop_process(tunnel)


if __name__ == "__main__":
    raise SystemExit(main())
