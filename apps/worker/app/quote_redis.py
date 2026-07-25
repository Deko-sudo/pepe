from __future__ import annotations

import uuid
from typing import Protocol


class RedisClient(Protocol):
    async def set(self, key: str, value: str, *, ex: int, nx: bool = False) -> bool | None: ...

    async def get(self, key: str) -> str | None: ...

    async def eval(self, script: str, numkeys: int, key: str, owner_token: str) -> int: ...


_COMPARE_AND_DELETE = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""


class QuoteRedisStore:
    """Redis cache and owner-safe per-instrument refresh leases.

    Redis is deliberately best-effort for cache writes. Lease failures are
    surfaced to callers because refreshing without mutual exclusion is unsafe.
    """

    def __init__(
        self,
        client: RedisClient,
        *,
        cache_namespace: str,
        cache_ttl_seconds: int,
        lease_ttl_seconds: int,
    ) -> None:
        self._client = client
        self._cache_namespace = cache_namespace
        self._cache_ttl_seconds = cache_ttl_seconds
        self._lease_ttl_seconds = lease_ttl_seconds

    async def set_cached_quote(self, instrument_id: uuid.UUID, payload: str) -> None:
        await self._client.set(
            self.cache_key(instrument_id),
            payload,
            ex=self._cache_ttl_seconds,
        )

    async def acquire_refresh_lease(self, instrument_id: uuid.UUID, owner_token: str) -> bool:
        acquired = await self._client.set(
            self.lease_key(instrument_id),
            owner_token,
            ex=self._lease_ttl_seconds,
            nx=True,
        )
        return bool(acquired)

    async def release_refresh_lease(self, instrument_id: uuid.UUID, owner_token: str) -> bool:
        deleted = await self._client.eval(
            _COMPARE_AND_DELETE,
            1,
            self.lease_key(instrument_id),
            owner_token,
        )
        return deleted == 1

    def cache_key(self, instrument_id: uuid.UUID) -> str:
        return f"{self._cache_namespace}:{instrument_id}"

    @staticmethod
    def lease_key(instrument_id: uuid.UUID) -> str:
        return f"pepe:quotes:refresh-lease:v1:{instrument_id}"
