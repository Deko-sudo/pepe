from __future__ import annotations

import uuid

import pytest

from app.quote_redis import QuoteRedisStore


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, tuple[str, int | None]] = {}

    async def set(self, key: str, value: str, *, ex: int, nx: bool = False) -> bool:
        if nx and key in self.values:
            return False
        self.values[key] = (value, ex)
        return True

    async def get(self, key: str) -> str | None:
        value = self.values.get(key)
        return None if value is None else value[0]

    async def eval(self, script: str, numkeys: int, key: str, owner_token: str) -> int:
        del script, numkeys
        if await self.get(key) != owner_token:
            return 0
        del self.values[key]
        return 1


def _store(redis: FakeRedis) -> QuoteRedisStore:
    return QuoteRedisStore(
        redis,
        cache_namespace="pepe:quotes:v1",
        cache_ttl_seconds=60,
        lease_ttl_seconds=120,
    )


@pytest.mark.asyncio
async def test_cache_key_matches_api_namespace_and_has_explicit_ttl() -> None:
    redis = FakeRedis()
    store = _store(redis)
    instrument_id = uuid.uuid4()

    await store.set_cached_quote(instrument_id, '{"schema_version":1,"quote":{}}')

    assert redis.values[f"pepe:quotes:v1:{instrument_id}"] == (
        '{"schema_version":1,"quote":{}}',
        60,
    )


@pytest.mark.asyncio
async def test_lease_rejects_second_owner_and_only_owner_can_release() -> None:
    redis = FakeRedis()
    store = _store(redis)
    instrument_id = uuid.uuid4()

    assert await store.acquire_refresh_lease(instrument_id, "owner-a") is True
    assert await store.acquire_refresh_lease(instrument_id, "owner-b") is False
    assert await store.release_refresh_lease(instrument_id, "owner-b") is False
    assert await store.release_refresh_lease(instrument_id, "owner-a") is True
    assert await store.acquire_refresh_lease(instrument_id, "owner-b") is True


@pytest.mark.asyncio
async def test_lease_key_is_stable_per_instrument_and_uses_approved_ttl() -> None:
    redis = FakeRedis()
    store = _store(redis)
    instrument_id = uuid.uuid4()

    assert await store.acquire_refresh_lease(instrument_id, "owner-a") is True

    assert redis.values[f"pepe:quotes:refresh-lease:v1:{instrument_id}"] == ("owner-a", 120)
