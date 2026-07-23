from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.schemas.auth import TelegramValidateRequest
from app.services.telegram_init_data import (
    TelegramInitDataError,
    validate_telegram_init_data,
)

router = APIRouter()


@router.post("/auth/telegram/validate")
async def validate_telegram_init_data_endpoint(
    body: TelegramValidateRequest,
) -> JSONResponse:
    if not settings.telegram_bot_token:
        return JSONResponse(
            status_code=503,
            content={"detail": "Проверка Telegram временно недоступна."},
        )

    try:
        result = validate_telegram_init_data(
            init_data=body.init_data,
            bot_token=settings.telegram_bot_token,
            max_age_seconds=settings.telegram_init_data_max_age_seconds,
            future_skew_seconds=settings.telegram_init_data_future_skew_seconds,
        )
    except TelegramInitDataError as e:
        if e.code == "unavailable":
            return JSONResponse(
                status_code=503,
                content={"detail": "Проверка Telegram временно недоступна."},
            )

        # invalid, expired, malformed — all return the same generic message
        return JSONResponse(
            status_code=401,
            content={"detail": "Не удалось подтвердить данные Telegram."},  # noqa: RUF001
        )

    return JSONResponse(status_code=200, content=result)
