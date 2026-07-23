from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from collections.abc import AsyncGenerator
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app

BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"  # noqa: S105
TEST_USER: dict[str, object] = {
    "id": 123456789,
    "first_name": "Иван",
    "last_name": "Петров",
    "username": "ivan_petrov",
    "language_code": "ru",
    "is_premium": True,
    "allows_write_to_pm": True,
    "photo_url": "https://example.com/photo.jpg",
}

GENERIC_ERROR = "Не удалось подтвердить данные Telegram."  # noqa: RUF001


def build_init_data(
    bot_token: str = BOT_TOKEN,
    user: dict[str, object] | None = None,
    auth_date: int | None = None,
    extra_pairs: dict[str, str] | None = None,
    skip_hash: bool = False,
    skip_auth_date: bool = False,
    skip_user: bool = False,
) -> str:
    if user is None:
        user = TEST_USER
    if auth_date is None:
        auth_date = int(time.time())

    pairs: list[tuple[str, str]] = []

    if not skip_auth_date:
        pairs.append(("auth_date", str(auth_date)))
    if not skip_user:
        pairs.append(("user", json.dumps(user, separators=(",", ":"), ensure_ascii=False)))
    if extra_pairs:
        for k, v in extra_pairs.items():
            pairs.append((k, v))

    sorted_pairs = sorted(pairs, key=lambda x: x[0])
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_pairs)

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not skip_hash:
        pairs.append(("hash", computed_hash))

    return "&".join(f"{k}={v}" for k, v in pairs)


# --- Static test vector (pre-computed, independent of helper) ---

STATIC_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"  # noqa: S105
STATIC_AUTH_DATE = 1710000000
STATIC_USER = '{"id":123456789,"first_name":"Test","username":"test_user"}'
STATIC_HASH = "d2b1599ee887023b24f005a20109718949effd444416ee1c3dd12ba0b7c2701a"
STATIC_INIT_DATA = (
    "auth_date=1710000000&user=%7B%22id%22%3A123456789%2C%22first_name%22"
    "%3A%22Test%22%2C%22username%22%3A%22test_user%22%7D&hash="
    "d2b1599ee887023b24f005a20109718949effd444416ee1c3dd12ba0b7c2701a"
)


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    with patch.object(settings, "telegram_bot_token", BOT_TOKEN):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.mark.asyncio
async def test_valid_init_data(client: AsyncClient) -> None:
    init_data = build_init_data()
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": init_data},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "valid"
    assert data["user"]["telegram_id"] == 123456789
    assert data["user"]["first_name"] == "Иван"


@pytest.mark.asyncio
async def test_valid_init_data_with_reordered_percent_encoded_pairs(
    client: AsyncClient,
) -> None:
    auth_date = 1710000000
    user = {"id": 987654321, "first_name": "Тест", "username": "test_user"}
    user_json = json.dumps(user, separators=(",", ":"), ensure_ascii=False)
    pairs = [
        ("user", user_json),
        ("query_id", "AAHdF6IQAAAAAN0XohDhrOrc"),
        ("auth_date", str(auth_date)),
    ]
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(pairs, key=lambda item: item[0])
    )
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=BOT_TOKEN.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    init_data = urlencode([*pairs, ("hash", signature)])

    with patch("app.services.telegram_init_data.time.time", return_value=float(auth_date)):
        response = await client.post(
            "/api/v1/auth/telegram/validate",
            json={"init_data": init_data},
        )

    assert response.status_code == 200
    assert response.json()["user"] == {
        "telegram_id": 987654321,
        "first_name": "Тест",
        "last_name": None,
        "username": "test_user",
        "language_code": None,
        "is_premium": False,
        "allows_write_to_pm": None,
        "photo_url": None,
    }


@pytest.mark.asyncio
async def test_static_test_vector(client: AsyncClient) -> None:
    with patch("app.services.telegram_init_data.time.time", return_value=float(STATIC_AUTH_DATE)):
        response = await client.post(
            "/api/v1/auth/telegram/validate",
            json={"init_data": STATIC_INIT_DATA},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "valid"
    assert data["user"]["telegram_id"] == 123456789


@pytest.mark.asyncio
async def test_tampered_user(client: AsyncClient) -> None:
    init_data = build_init_data(user=TEST_USER)
    original_user_str = json.dumps(TEST_USER, separators=(",", ":"), ensure_ascii=False)
    tampered_user: dict[str, object] = {**TEST_USER, "id": 999999999}
    tampered_user_str = json.dumps(tampered_user, separators=(",", ":"), ensure_ascii=False)
    init_data = init_data.replace(
        f"user={original_user_str}",
        f"user={tampered_user_str}",
    )
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": init_data},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


@pytest.mark.asyncio
async def test_tampered_hash(client: AsyncClient) -> None:
    init_data = build_init_data()
    init_data = init_data.replace(
        init_data.split("hash=")[1], "a" * 64,
    )
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": init_data},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


@pytest.mark.asyncio
async def test_wrong_bot_token(client: AsyncClient) -> None:
    init_data = build_init_data(bot_token="wrong_token")  # noqa: S106
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": init_data},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


@pytest.mark.asyncio
async def test_missing_hash(client: AsyncClient) -> None:
    auth_date = int(time.time())
    user_str = json.dumps(TEST_USER, separators=(",", ":"), ensure_ascii=False)
    init_data = f"auth_date={auth_date}&user={user_str}"
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": init_data},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


@pytest.mark.asyncio
async def test_missing_auth_date(client: AsyncClient) -> None:
    user_str = json.dumps(TEST_USER, separators=(",", ":"), ensure_ascii=False)
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=BOT_TOKEN.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    computed_hash = hmac.new(
        key=secret_key,
        msg=f"user={user_str}".encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    init_data = urlencode([("user", user_str), ("hash", computed_hash)])
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": init_data},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


@pytest.mark.asyncio
async def test_missing_user(client: AsyncClient) -> None:
    auth_date = int(time.time())
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=BOT_TOKEN.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    data_check = f"auth_date={auth_date}"
    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    init_data = f"auth_date={auth_date}&hash={computed_hash}"
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": init_data},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


@pytest.mark.asyncio
async def test_expired_auth_date(client: AsyncClient) -> None:
    expired_date = int(time.time()) - 7200
    init_data = build_init_data(auth_date=expired_date)
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": init_data},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


@pytest.mark.asyncio
async def test_future_auth_date(client: AsyncClient) -> None:
    future_date = int(time.time()) + 3600
    init_data = build_init_data(auth_date=future_date)
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": init_data},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


@pytest.mark.asyncio
async def test_malformed_user_json(client: AsyncClient) -> None:
    auth_date = int(time.time())
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=BOT_TOKEN.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    bad_user = "not-valid-json"
    data_check = f"auth_date={auth_date}\nuser={bad_user}"
    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    init_data = f"auth_date={auth_date}&hash={computed_hash}&user={bad_user}"
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": init_data},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


@pytest.mark.asyncio
async def test_duplicate_hash_key(client: AsyncClient) -> None:
    auth_date = int(time.time())
    user_str = json.dumps(TEST_USER, separators=(",", ":"), ensure_ascii=False)
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=BOT_TOKEN.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    computed_hash = hmac.new(
        key=secret_key,
        msg=f"auth_date={auth_date}\nuser={user_str}".encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    init_data = urlencode(
        [
            ("auth_date", str(auth_date)),
            ("user", user_str),
            ("hash", computed_hash),
            ("hash", computed_hash),
        ],
    )
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": init_data},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


@pytest.mark.asyncio
async def test_duplicate_unknown_key(client: AsyncClient) -> None:
    auth_date = int(time.time())
    user_str = json.dumps(TEST_USER, separators=(",", ":"), ensure_ascii=False)
    pairs = [
        ("auth_date", str(auth_date)),
        ("user", user_str),
        ("custom", "abc"),
        ("custom", "def"),
    ]
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(pairs, key=lambda item: item[0])
    )
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=BOT_TOKEN.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    init_data = urlencode([*pairs, ("hash", computed_hash)])
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": init_data},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


@pytest.mark.asyncio
async def test_too_long_input(client: AsyncClient) -> None:
    long_data = "a" * (17 * 1024)
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": long_data},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


@pytest.mark.asyncio
async def test_empty_init_data(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": ""},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR


@pytest.mark.asyncio
async def test_unicode_in_user_fields(client: AsyncClient) -> None:
    user: dict[str, object] = {**TEST_USER, "first_name": "Иван", "username": "ivan_петров"}
    init_data = build_init_data(user=user)
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": init_data},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_secrets_not_in_response(client: AsyncClient) -> None:
    init_data = build_init_data()
    response = await client.post(
        "/api/v1/auth/telegram/validate",
        json={"init_data": init_data},
    )
    body = response.text
    assert BOT_TOKEN not in body
    assert "secret_key" not in body
    assert "WebAppData" not in body


@pytest.mark.asyncio
async def test_secrets_not_in_logs(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    init_data = build_init_data()
    with caplog.at_level(logging.INFO):
        await client.post(
            "/api/v1/auth/telegram/validate",
            json={"init_data": init_data},
        )
    for record in caplog.records:
        assert BOT_TOKEN not in record.message
        assert "WebAppData" not in record.message
        assert "secret_key" not in record.message
