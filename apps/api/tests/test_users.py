from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from collections.abc import AsyncGenerator, AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db.session import get_db
from app.main import app

BOT_TOKEN = "test"  # noqa: S105
GENERIC_ERROR = "Не удалось подтвердить данные Telegram."  # noqa: RUF001
TEST_USER = {
    "id": 123456789,
    "first_name": "Иван",
    "last_name": "Петров",
    "username": "ivan_petrov",
    "language_code": "ru",
    "is_premium": True,
    "allows_write_to_pm": True,
    "photo_url": "https://example.com/photo.jpg",
}


class FakeResult:
    def __init__(self, user: SimpleNamespace) -> None:
        self._user = user

    def scalar_one(self) -> SimpleNamespace:
        return self._user


class FakeDatabaseSession:
    def __init__(self, user: SimpleNamespace) -> None:
        self.user = user
        self.statements: list[object] = []

    async def execute(self, statement: object) -> FakeResult:
        self.statements.append(statement)
        return FakeResult(self.user)


def build_init_data() -> str:
    auth_date = int(time.time())
    user_json = json.dumps(TEST_USER, separators=(",", ":"), ensure_ascii=False)
    data_check_string = f"auth_date={auth_date}\nuser={user_json}"
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=BOT_TOKEN.encode(),
        digestmod=hashlib.sha256,
    ).digest()
    signature = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"auth_date={auth_date}&user={user_json}&hash={signature}"


@pytest.fixture
async def client() -> AsyncGenerator[tuple[AsyncClient, FakeDatabaseSession], None]:
    now = datetime.now(UTC)
    persisted_user = SimpleNamespace(
        id=uuid.uuid4(),
        telegram_id=TEST_USER["id"],
        first_name=TEST_USER["first_name"],
        last_name=TEST_USER["last_name"],
        username=TEST_USER["username"],
        language_code=TEST_USER["language_code"],
        is_premium=TEST_USER["is_premium"],
        allows_write_to_pm=TEST_USER["allows_write_to_pm"],
        photo_url=TEST_USER["photo_url"],
        created_at=now,
        updated_at=now,
    )
    db = FakeDatabaseSession(persisted_user)

    async def override_db() -> AsyncIterator[FakeDatabaseSession]:
        yield db

    app.dependency_overrides[get_db] = override_db
    with patch.object(settings, "telegram_bot_token", BOT_TOKEN):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            yield async_client, db
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_me_returns_upserted_user_after_verified_init_data(
    client: tuple[AsyncClient, FakeDatabaseSession],
) -> None:
    http_client, db = client

    response = await http_client.post(
        "/api/v1/users/me",
        json={"init_data": build_init_data()},
    )

    assert response.status_code == 200
    assert response.json()["telegram_id"] == TEST_USER["id"]
    assert response.json()["first_name"] == TEST_USER["first_name"]
    assert len(db.statements) == 2


@pytest.mark.asyncio
async def test_me_does_not_upsert_unverified_init_data(
    client: tuple[AsyncClient, FakeDatabaseSession],
) -> None:
    http_client, db = client

    response = await http_client.post(
        "/api/v1/users/me",
        json={"init_data": f"{build_init_data()}0"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == GENERIC_ERROR
    assert db.statements == []
