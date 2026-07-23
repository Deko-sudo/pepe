from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.modules.users.service import upsert_telegram_user
from app.schemas.auth import TelegramValidateRequest, TelegramValidateResponse
from app.services.telegram_init_data import (
    TelegramInitDataError,
    validate_telegram_init_data,
)

router = APIRouter()


def validate_telegram_request(
    body: TelegramValidateRequest,
) -> TelegramValidateResponse:
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
    except TelegramInitDataError as e:
        if e.code == "unavailable":
            raise HTTPException(
                status_code=503,
                detail="Проверка Telegram временно недоступна.",
            ) from e

        raise HTTPException(
            status_code=401,
            detail="Не удалось подтвердить данные Telegram.",  # noqa: RUF001
        ) from e

    return TelegramValidateResponse.model_validate(result)


@router.post("/auth/telegram/validate", response_model=TelegramValidateResponse)
async def validate_telegram_init_data_endpoint(
    body: TelegramValidateRequest,
    db: AsyncSession = Depends(get_db),
) -> TelegramValidateResponse:
    validation = validate_telegram_request(body)
    await upsert_telegram_user(db, validation.user)
    return validation
