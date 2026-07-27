from __future__ import annotations

import uuid
from typing import Protocol

from pepe_quote_core import CandleTimeframe

_COMPARE_AND_DELETE = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""


class RedisClient(Protocol):
    async def set(self, key: str, value: str, *, ex: int, nx: bool = False) -> bool | None: ...

    async def eval(self, script: str, numkeys: int, key: str, owner_token: str) -> int: ...


class CandleRedisLeaseStore:
    """Owner-safe, non-renewing mutual exclusion for one instrument/timeframe sync."""

    def __init__(self, client: RedisClient, *, lease_ttl_seconds: int = 300) -> None:
        self._client = client
        self._lease_ttl_seconds = lease_ttl_seconds

    async def acquire(
        self, instrument_id: uuid.UUID, timeframe: CandleTimeframe, owner_token: str,
    ) -> bool:
        acquired = await self._client.set(
            self.lease_key(instrument_id, timeframe),
            owner_token,
            ex=self._lease_ttl_seconds,
            nx=True,
        )
        return bool(acquired)

    async def release(
        self, instrument_id: uuid.UUID, timeframe: CandleTimeframe, owner_token: str,
    ) -> bool:
        deleted = await self._client.eval(
            _COMPARE_AND_DELETE,
            1,
            self.lease_key(instrument_id, timeframe),
            owner_token,
        )
        return deleted == 1

    @staticmethod
    def lease_key(instrument_id: uuid.UUID, timeframe: CandleTimeframe) -> str:
        return f"pepe:candles:sync-lease:v1:{instrument_id}:{timeframe.value}"
