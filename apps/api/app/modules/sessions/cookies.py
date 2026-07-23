from __future__ import annotations

from datetime import datetime

from fastapi import Response

from app.core.config import settings


def set_session_cookie(response: Response, *, token: str, expires_at: datetime) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_absolute_ttl_seconds,
        expires=expires_at,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )
