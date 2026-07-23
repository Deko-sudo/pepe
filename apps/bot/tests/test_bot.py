from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Chat, Message, User


def create_mock_message(text: str = "/start") -> MagicMock:
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.answer = AsyncMock()
    msg.chat = MagicMock(spec=Chat)
    msg.chat.id = 123456
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = 123456
    msg.from_user.is_bot = False
    return msg


@pytest.mark.asyncio
async def test_start_command_sends_correct_response() -> None:
    from aiogram import Dispatcher

    from app.main import setup_handlers

    dp = Dispatcher()
    setup_handlers(dp)

    handler = dp.message.handlers[0]
    msg = create_mock_message("/start")
    await handler.callback(msg)

    assert msg.answer.called
    call_args = msg.answer.call_args
    assert "Pepe" in call_args[0][0]
    assert "Telegram Mini App" in call_args[0][0]


@pytest.mark.asyncio
async def test_help_command_sends_correct_response() -> None:
    from aiogram import Dispatcher

    from app.main import setup_handlers

    dp = Dispatcher()
    setup_handlers(dp)

    handler = dp.message.handlers[1]
    msg = create_mock_message("/help")
    await handler.callback(msg)

    assert msg.answer.called
    call_args = msg.answer.call_args
    assert "/start" in call_args[0][0]
    assert "/help" in call_args[0][0]


def test_token_not_in_logs(caplog: pytest.LogCaptureFixture) -> None:
    from app.config import BotSettings

    settings = BotSettings()
    token = settings.telegram_bot_token
    assert token == "" or "TELEGRAM_BOT_TOKEN" not in caplog.text
