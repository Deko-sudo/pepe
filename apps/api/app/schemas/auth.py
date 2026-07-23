from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TelegramValidateRequest(BaseModel):
    init_data: str


class TelegramUser(BaseModel):
    telegram_id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool = False
    allows_write_to_pm: bool | None = None
    photo_url: str | None = None


class TelegramValidateResponse(BaseModel):
    status: str
    auth_date: int
    user: TelegramUser


class UserProfile(TelegramUser):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
