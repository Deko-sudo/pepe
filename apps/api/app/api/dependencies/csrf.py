from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import urlsplit

from fastapi import HTTPException
from starlette.requests import Request

from app.core.config import settings

CSRF_ERROR = "Forbidden."


def _origin_from_url(value: str) -> str | None:
    if value == "null":
        return None

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None

    hostname = parsed.hostname
    if (
        parsed.scheme not in {"http", "https"}
        or hostname is None
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None

    default_port = 80 if parsed.scheme == "http" else 443
    authority_hostname = f"[{hostname}]" if ":" in hostname else hostname
    authority = (
        authority_hostname
        if port in {None, default_port}
        else f"{authority_hostname}:{port}"
    )
    return f"{parsed.scheme}://{authority}"


def _is_allowed_origin(value: str, allowed_origins: Sequence[str]) -> bool:
    return value in allowed_origins


async def require_session_csrf(
    request: Request,
    allowed_origins: Sequence[str],
) -> None:
    origin = request.headers.get("origin")
    if origin is not None:
        if not _is_allowed_origin(origin, allowed_origins):
            raise HTTPException(status_code=403, detail=CSRF_ERROR)
        return

    referer = request.headers.get("referer")
    referer_origin = _origin_from_url(referer) if referer is not None else None
    if referer_origin is None or not _is_allowed_origin(referer_origin, allowed_origins):
        raise HTTPException(status_code=403, detail=CSRF_ERROR)


async def require_configured_session_csrf(request: Request) -> None:
    await require_session_csrf(request, settings.session_origins)
