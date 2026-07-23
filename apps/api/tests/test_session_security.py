from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.dependencies.csrf import require_session_csrf
from app.core.config import Settings
from app.modules.sessions.service import (
    SESSION_TOKEN_BYTES,
    clamp_idle_expiry,
    digest_session_token,
    generate_session_token,
)


def make_request(headers: dict[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/logout",
            "headers": [(key.encode(), value.encode()) for key, value in headers.items()],
        },
    )


def test_session_token_uses_at_least_256_bits_of_entropy() -> None:
    assert SESSION_TOKEN_BYTES >= 32
    assert generate_session_token() != generate_session_token()


def test_session_token_digest_is_sha256_hex_without_returning_raw_token() -> None:
    token = generate_session_token()

    digest = digest_session_token(token)

    assert digest == hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert len(digest) == 64
    assert token not in digest


def test_sliding_idle_expiry_never_crosses_absolute_expiry() -> None:
    now = datetime(2026, 7, 24, tzinfo=UTC)
    absolute_expiry = now + timedelta(hours=1)

    result = clamp_idle_expiry(
        now=now,
        absolute_expiry=absolute_expiry,
        idle_ttl_seconds=7 * 24 * 60 * 60,
    )

    assert result == absolute_expiry


def test_settings_rejects_non_approved_active_session_limit() -> None:
    with pytest.raises(ValueError, match="session_max_active"):
        Settings(session_max_active=6)


def test_settings_rejects_production_without_allowed_session_origins() -> None:
    with pytest.raises(ValueError, match="session_allowed_origins"):
        Settings(
            environment="production",
            session_cookie_secure=True,
            session_allowed_origins="",
        )


def test_settings_rejects_wildcard_or_non_origin_session_origin() -> None:
    with pytest.raises(ValueError, match="absolute HTTP/HTTPS origins"):
        Settings(session_allowed_origins="https://*.example.com")

    with pytest.raises(ValueError, match="absolute HTTP/HTTPS origins"):
        Settings(session_allowed_origins="https://example.com/path")


@pytest.mark.asyncio
async def test_csrf_accepts_exact_allowed_origin() -> None:
    request = make_request({"origin": "https://mini.pepe.example"})

    await require_session_csrf(request, allowed_origins=("https://mini.pepe.example",))


@pytest.mark.asyncio
async def test_csrf_rejects_disallowed_origin_without_referer_fallback() -> None:
    request = make_request(
        {
            "origin": "https://evil.example",
            "referer": "https://mini.pepe.example/settings",
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        await require_session_csrf(request, allowed_origins=("https://mini.pepe.example",))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Forbidden."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [
        {"origin": "null"},
        {"origin": "https://mini.pepe.example.evil.example"},
        {"origin": "http://mini.pepe.example"},
        {"origin": "https://mini.pepe.example:444"},
        {},
        {"referer": "not a url"},
        {"referer": "https://mini.pepe.example.evil.example/path"},
    ],
)
async def test_csrf_rejects_invalid_or_malicious_origins(headers: dict[str, str]) -> None:
    request = make_request(headers)

    with pytest.raises(HTTPException) as exc_info:
        await require_session_csrf(request, allowed_origins=("https://mini.pepe.example",))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Forbidden."


@pytest.mark.asyncio
async def test_csrf_uses_allowed_referer_only_when_origin_is_absent() -> None:
    request = make_request({"referer": "https://mini.pepe.example/settings?tab=security"})

    await require_session_csrf(request, allowed_origins=("https://mini.pepe.example",))
