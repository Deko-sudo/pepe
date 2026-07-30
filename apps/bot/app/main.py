import asyncio
import logging
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import bot_settings

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


def create_bot() -> Bot | None:
    token = bot_settings.telegram_bot_token
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN is empty. Running in dev idle mode.")
        return None
    return Bot(token=token)


def versioned_mini_app_url(base_url: str, build_id: str) -> str:
    parts = urlsplit(base_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["v"] = build_id
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def setup_handlers(dp: Dispatcher) -> None:
    @dp.message(CommandStart())
    async def cmd_start(message: types.Message) -> None:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Открыть Pepe",
            web_app=types.WebAppInfo(
                url=versioned_mini_app_url(
                    bot_settings.mini_app_url,
                    bot_settings.mini_app_build_id,
                ),
            ),
        )
        builder.adjust(1)

        await message.answer(
            "Pepe \u2014 Telegram Mini App для рыночной аналитики.\n\n"
            "Откройте приложение, чтобы просмотреть демонстрационный интерфейс.",
            reply_markup=builder.as_markup(),
        )

    @dp.message(Command("help"))
    async def cmd_help(message: types.Message) -> None:
        await message.answer(
            "Доступные команды:\n"
            "/start \u2014 Запустить приложение\n"
            "/help \u2014 Показать эту справку",
        )


async def run_polling() -> None:
    bot = create_bot()
    if bot is None:
        logger.info("Bot is in dev idle mode. Waiting for shutdown signal...")
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Bot shutting down...")
        return

    dp = Dispatcher()
    setup_handlers(dp)

    try:
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    finally:
        logger.info("Bot shutting down...")
        await bot.session.close()


def main() -> None:
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
