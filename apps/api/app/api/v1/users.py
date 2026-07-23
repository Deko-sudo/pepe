from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import validate_telegram_request
from app.db.session import get_db
from app.modules.users.service import get_user_by_telegram_id, upsert_telegram_user
from app.schemas.auth import TelegramValidateRequest, UserProfile

router = APIRouter(prefix="/users")


@router.post("/me", response_model=UserProfile)
async def get_current_user(
    body: TelegramValidateRequest,
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    validation = validate_telegram_request(body)
    await upsert_telegram_user(db, validation.user)
    user = await get_user_by_telegram_id(db, validation.user.telegram_id)
    return UserProfile.model_validate(user)
