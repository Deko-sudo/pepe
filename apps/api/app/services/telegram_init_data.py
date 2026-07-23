from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from urllib.parse import parse_qsl

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
            "Malformed init data.",
            "malformed",
        )

    if len(init_data) > MAX_INIT_DATA_LENGTH:
        raise TelegramInitDataError(
            "Malformed init data.",
            "malformed",
        )

    # Step 1: Parse all key=value pairs (preserve order for duplicate check)
    raw_pairs = parse_qsl(init_data, keep_blank_values=True)

    if not raw_pairs:
        raise TelegramInitDataError(
            "Malformed init data.",
            "malformed",
        )

    # Step 2: Reject ANY duplicate keys
    seen_keys: set[str] = set()
    for key, _value in raw_pairs:
        if key in seen_keys:
            raise TelegramInitDataError(
                "Malformed init data.",
                "malformed",
            )
        seen_keys.add(key)

    # Step 3: Check required fields
    pairs_dict = dict(raw_pairs)
    for required in ("hash", "auth_date", "user"):
        if required not in pairs_dict:
            raise TelegramInitDataError(
                "Malformed init data.",
                "malformed",
            )

    received_hash = pairs_dict["hash"]

    # Step 4: Validate hash format (64 hex chars)
    if len(received_hash) != HASH_LENGTH:
        raise TelegramInitDataError(
            "Invalid signature.",
            "invalid",
        )

    try:
        bytes.fromhex(received_hash)
    except ValueError as err:
        raise TelegramInitDataError(
            "Invalid signature.",
            "invalid",
        ) from err

    # Step 5: Build data-check-string (exclude hash, sort by key)
    data_check_pairs = []
    for key, value in raw_pairs:
        if key == "hash":
            continue
        data_check_pairs.append(f"{key}={value}")
    data_check_string = "\n".join(data_check_pairs)

    # Step 6: HMAC-SHA-256 verification (BEFORE parsing user/auth_date)
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
        logger.info("event=telegram_init_data_validation result=invalid")
        raise TelegramInitDataError(
            "Invalid signature.",
            "invalid",
        )

    # Step 7: ONLY AFTER successful HMAC — parse auth_date
    try:
        auth_date = int(pairs_dict["auth_date"])
    except (ValueError, TypeError) as err:
        logger.info("event=telegram_init_data_validation result=malformed")
        raise TelegramInitDataError(
            "Malformed init data.",
            "malformed",
        ) from err

    # Step 8: Check auth_date freshness
    now = _now if _now is not None else time.time()

    if now - auth_date > max_age_seconds:
        logger.info("event=telegram_init_data_validation result=expired")
        raise TelegramInitDataError(
            "Invalid signature.",
            "expired",
        )

    if auth_date > now + future_skew_seconds:
        logger.info("event=telegram_init_data_validation result=expired")
        raise TelegramInitDataError(
            "Invalid signature.",
            "expired",
        )

    # Step 9: ONLY AFTER successful HMAC — parse user JSON
    try:
        user_data = json.loads(pairs_dict["user"])
    except (json.JSONDecodeError, TypeError) as err:
        logger.info("event=telegram_init_data_validation result=malformed")
        raise TelegramInitDataError(
            "Malformed init data.",
            "malformed",
        ) from err

    if not isinstance(user_data, dict):
        logger.info("event=telegram_init_data_validation result=malformed")
        raise TelegramInitDataError(
            "Malformed init data.",
            "malformed",
        )

    telegram_id = user_data.get("id")
    if not isinstance(telegram_id, int):
        logger.info("event=telegram_init_data_validation result=malformed")
        raise TelegramInitDataError(
            "Malformed init data.",
            "malformed",
        )

    if telegram_id < -(2**63) or telegram_id > 2**63 - 1:
        logger.info("event=telegram_init_data_validation result=malformed")
        raise TelegramInitDataError(
            "Malformed init data.",
            "malformed",
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
