from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from urllib.parse import parse_qs

logger = logging.getLogger(__name__)

MAX_INIT_DATA_LENGTH = 16 * 1024
HASH_LENGTH = 64


class TelegramInitDataError(Exception):
    def __init__(self, message: str, code: str) -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def validate_telegram_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 3600,
    future_skew_seconds: int = 30,
    _now: float | None = None,
) -> dict[str, object]:
    if not bot_token:
        raise TelegramInitDataError(
            "Проверка Telegram временно недоступна.",
            "unavailable",
        )

    if not init_data:
        raise TelegramInitDataError(
            "init_data is required.",
            "malformed",
        )

    if len(init_data) > MAX_INIT_DATA_LENGTH:
        raise TelegramInitDataError(
            "init_data is too long.",
            "malformed",
        )

    pairs = parse_qs(init_data, keep_blank_values=False)

    for key in ("hash", "auth_date", "user"):
        if key not in pairs:
            raise TelegramInitDataError(
                "Missing required field.",
                "malformed",
            )

    if len(pairs.get("hash", [])) > 1:
        raise TelegramInitDataError("Duplicate key.", "malformed")
    if len(pairs.get("auth_date", [])) > 1:
        raise TelegramInitDataError("Duplicate key.", "malformed")
    if len(pairs.get("user", [])) > 1:
        raise TelegramInitDataError("Duplicate key.", "malformed")

    received_hash = pairs["hash"][0]
    if len(received_hash) != HASH_LENGTH:
        raise TelegramInitDataError("Invalid signature.", "invalid")

    try:
        bytes.fromhex(received_hash)
    except ValueError as err:
        raise TelegramInitDataError("Invalid signature.", "invalid") from err

    auth_date_str = pairs["auth_date"][0]
    try:
        auth_date = int(auth_date_str)
    except (ValueError, TypeError) as err:
        raise TelegramInitDataError("Invalid auth_date.", "malformed") from err

    user_str = pairs["user"][0]
    try:
        user_data = json.loads(user_str)
    except (json.JSONDecodeError, TypeError) as err:
        raise TelegramInitDataError("Malformed user data.", "malformed") from err

    if not isinstance(user_data, dict):
        raise TelegramInitDataError("Malformed user data.", "malformed")

    telegram_id = user_data.get("id")
    if not isinstance(telegram_id, int):
        raise TelegramInitDataError("Invalid user id.", "malformed")

    if telegram_id < -(2**63) or telegram_id > 2**63 - 1:
        raise TelegramInitDataError("Invalid user id.", "malformed")

    now = _now if _now is not None else time.time()

    if now - auth_date > max_age_seconds:
        raise TelegramInitDataError("Init data expired.", "expired")

    if auth_date > now + future_skew_seconds:
        raise TelegramInitDataError("Init data from the future.", "expired")

    data_check_pairs = []
    for key in sorted(pairs.keys()):
        if key == "hash":
            continue
        data_check_pairs.append(f"{key}={pairs[key][0]}")
    data_check_string = "\n".join(data_check_pairs)

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        logger.info(
            "event=telegram_init_data_validation result=invalid",
        )
        raise TelegramInitDataError(
            "Не удалось подтвердить данные Telegram.",  # noqa: RUF001
            "invalid",
        )

    logger.info("event=telegram_init_data_validation result=success")

    return {
        "status": "valid",
        "auth_date": auth_date,
        "user": {
            "telegram_id": user_data["id"],
            "first_name": user_data.get("first_name", ""),
            "last_name": user_data.get("last_name"),
            "username": user_data.get("username"),
            "language_code": user_data.get("language_code"),
            "is_premium": user_data.get("is_premium", False),
            "allows_write_to_pm": user_data.get("allows_write_to_pm"),
            "photo_url": user_data.get("photo_url"),
        },
    }
