from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.modules.sessions.service import (
    AuthenticatedSession,
    resolve_authenticated_session,
    utc_now,
)

AUTH_ERROR = "Unauthorized."


async def require_current_session(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthenticatedSession:
    auth = await resolve_authenticated_session(
        db,
        request.cookies.get(settings.session_cookie_name),
        idle_ttl_seconds=settings.session_idle_ttl_seconds,
        now=utc_now(),
    )
    if auth is None:
        raise HTTPException(status_code=401, detail=AUTH_ERROR)
    return auth
