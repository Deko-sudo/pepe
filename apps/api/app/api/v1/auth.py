from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.csrf import require_configured_session_csrf
from app.api.dependencies.session import get_presented_session_token, require_current_session
from app.core.config import settings
from app.db.session import get_db
from app.modules.sessions.cookies import clear_session_cookie, set_session_cookie
from app.modules.sessions.service import (
    AuthenticatedSession,
    create_session,
    revoke_all_active_sessions,
    revoke_presented_session,
    utc_now,
)
from app.modules.sessions.transport import SESSION_FALLBACK_HEADER, session_fallback_requested
from app.modules.users.service import get_user_by_telegram_id, upsert_telegram_user
from app.schemas.auth import (
    TelegramValidateRequest,
    TelegramValidateResponse,
    UserProfile,
)
from app.services.telegram_init_data import TelegramInitDataError, validate_telegram_init_data

router = APIRouter()


def validate_telegram_request(body: TelegramValidateRequest) -> TelegramValidateResponse:
    if not settings.telegram_bot_token:
        raise HTTPException(
            status_code=503,
            detail="Проверка Telegram временно недоступна.",
        )
    try:
        result = validate_telegram_init_data(
            init_data=body.init_data,
            bot_token=settings.telegram_bot_token,
            max_age_seconds=settings.telegram_init_data_max_age_seconds,
            future_skew_seconds=settings.telegram_init_data_future_skew_seconds,
        )
    except TelegramInitDataError as error:
        if error.code == "unavailable":
            raise HTTPException(
                status_code=503,
                detail="Проверка Telegram временно недоступна.",
            ) from error
        raise HTTPException(
            status_code=401,
            detail="Не удалось подтвердить данные Telegram.",  # noqa: RUF001
        ) from error
    return TelegramValidateResponse.model_validate(result)


@router.post("/auth/telegram/validate", response_model=TelegramValidateResponse)
async def validate_telegram_init_data_endpoint(
    body: TelegramValidateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TelegramValidateResponse:
    validation = validate_telegram_request(body)
    await upsert_telegram_user(db, validation.user)
    return validation


@router.post(
    "/auth/telegram/session",
    response_model=UserProfile,
    responses={
        200: {
            "headers": {
                SESSION_FALLBACK_HEADER: {
                    "description": ("Conditional in-memory session fallback for Telegram Desktop."),
                    "schema": {"type": "string"},
                },
            },
        },
    },
)
async def exchange_telegram_session(
    body: TelegramValidateRequest,
    request: Request,
    response: Response,
    _: Annotated[None, Depends(require_configured_session_csrf)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProfile:
    validation = validate_telegram_request(body)
    await upsert_telegram_user(db, validation.user)
    user = await get_user_by_telegram_id(db, validation.user.telegram_id)
    now = utc_now()
    await revoke_presented_session(
        db,
        get_presented_session_token(request),
        now=now,
    )
    session, token = await create_session(
        db,
        user,
        absolute_ttl_seconds=settings.session_absolute_ttl_seconds,
        idle_ttl_seconds=settings.session_idle_ttl_seconds,
        max_active_sessions=settings.session_max_active,
        now=now,
    )
    set_session_cookie(response, token=token, expires_at=session.expires_at)
    if session_fallback_requested(request.headers):
        response.headers[SESSION_FALLBACK_HEADER] = token
    response.headers["Cache-Control"] = "no-store"
    profile = UserProfile.model_validate(user)
    return profile


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    _: Annotated[None, Depends(require_configured_session_csrf)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await revoke_presented_session(
        db,
        get_presented_session_token(request),
        now=utc_now(),
    )
    clear_session_cookie(response)


@router.post("/auth/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    response: Response,
    _: Annotated[None, Depends(require_configured_session_csrf)],
    auth: Annotated[AuthenticatedSession, Depends(require_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await revoke_all_active_sessions(db, auth.user.id, now=utc_now())
    clear_session_cookie(response)
