from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.db.models.user import User
from app.schemas.auth import TelegramUser


async def upsert_telegram_user(db: AsyncSession, telegram_user: TelegramUser) -> None:
    user_values = telegram_user.model_dump()
    statement = insert(User).values(**user_values).on_conflict_do_update(
        index_elements=[User.telegram_id],
        set_={
            **user_values,
            "updated_at": func.now(),
        },
    )
    await db.execute(statement)


async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> User:
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one()
