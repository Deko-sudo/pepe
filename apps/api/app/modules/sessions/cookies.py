from __future__ import annotations

from datetime import datetime

from fastapi import Response

from app.core.config import settings


def _append_partitioned_attribute(response: Response) -> None:
    for index in range(len(response.raw_headers) - 1, -1, -1):
        name, value = response.raw_headers[index]
        if name == b"set-cookie":
            response.raw_headers[index] = (name, value + b"; Partitioned")
            return
    raise RuntimeError("set-cookie header was not created")


def set_session_cookie(response: Response, *, token: str, expires_at: datetime) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_absolute_ttl_seconds,
        expires=expires_at,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_same_site,
    )
    if settings.session_cookie_partitioned:
        _append_partitioned_attribute(response)


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_same_site,
    )
    if settings.session_cookie_partitioned:
        _append_partitioned_attribute(response)
