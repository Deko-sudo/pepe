from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, TypeAlias

from pepe_quote_core import NormalizedQuote, QuoteRequest

logger = logging.getLogger(__name__)


class LeaseStore(Protocol):
    async def acquire_refresh_lease(self, instrument_id: uuid.UUID, owner_token: str) -> bool: ...

    async def release_refresh_lease(self, instrument_id: uuid.UUID, owner_token: str) -> bool: ...


class QuoteProvider(Protocol):
    async def fetch_quotes(
        self, requests: Iterable[QuoteRequest],
    ) -> tuple[NormalizedQuote, ...]: ...


class QuoteUnitOfWork(Protocol):
    """A transaction that makes persistence atomic before cache publication."""

    async def upsert(self, quote: NormalizedQuote) -> bool: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class QuoteUnitOfWorkFactory(Protocol):
    async def create(self) -> QuoteUnitOfWork: ...


class QuoteCache(Protocol):
    async def set_cached_quote(self, quote: NormalizedQuote) -> None: ...


@dataclass(frozen=True, slots=True)
class RefreshTarget:
    request: QuoteRequest

    @property
    def instrument_id(self) -> uuid.UUID:
        return self.request.instrument_id


class SkipReason(StrEnum):
    LEASE_HELD = "lease_held"


class RetryReason(StrEnum):
    LEASE_UNAVAILABLE = "lease_unavailable"
    PROVIDER_FAILED = "provider_failed"
    INVALID_PROVIDER_RESPONSE = "invalid_provider_response"
    PERSISTENCE_FAILED = "persistence_failed"


@dataclass(frozen=True, slots=True)
class RefreshSuccess:
    instrument_id: uuid.UUID
    cache_written: bool


@dataclass(frozen=True, slots=True)
class RefreshSkipped:
    instrument_id: uuid.UUID
    reason: SkipReason


@dataclass(frozen=True, slots=True)
class RefreshRetryable:
    instrument_id: uuid.UUID
    reason: RetryReason


RefreshResult: TypeAlias = RefreshSuccess | RefreshSkipped | RefreshRetryable  # noqa: UP040


class QuoteRefreshService:
    """Refreshes one instrument under an owner-safe, non-renewing Redis lease.

    The concrete database and cache implementations are intentionally ports. This
    keeps the orchestration testable without importing the API application's ORM
    or creating a real database in worker service tests.
    """

    def __init__(
        self,
        *,
        leases: LeaseStore,
        provider: QuoteProvider,
        unit_of_work_factory: QuoteUnitOfWorkFactory,
        cache: QuoteCache,
        owner_token_factory: Callable[[], str] | None = None,
    ) -> None:
        self._leases = leases
        self._provider = provider
        self._unit_of_work_factory = unit_of_work_factory
        self._cache = cache
        self._owner_token_factory = owner_token_factory or (lambda: str(uuid.uuid4()))

    async def refresh(self, target: RefreshTarget) -> RefreshResult:
        """Run lease -> provider -> validate -> UoW commit -> cache -> release for one target."""
        owner_token = self._owner_token_factory()
        try:
            acquired = await self._leases.acquire_refresh_lease(target.instrument_id, owner_token)
        except Exception:
            # Without a lease, provider work must not begin.
            return RefreshRetryable(target.instrument_id, RetryReason.LEASE_UNAVAILABLE)

        if not acquired:
            return RefreshSkipped(target.instrument_id, SkipReason.LEASE_HELD)

        try:
            try:
                quotes = await self._provider.fetch_quotes((target.request,))
            except Exception:
                return RefreshRetryable(target.instrument_id, RetryReason.PROVIDER_FAILED)

            if len(quotes) != 1 or quotes[0].instrument_id != target.instrument_id:
                return RefreshRetryable(target.instrument_id, RetryReason.INVALID_PROVIDER_RESPONSE)
            quote = quotes[0]

            unit_of_work: QuoteUnitOfWork | None = None
            try:
                unit_of_work = await self._unit_of_work_factory.create()
                accepted = await unit_of_work.upsert(quote)
                await unit_of_work.commit()
            except Exception:
                if unit_of_work is not None:
                    try:
                        await unit_of_work.rollback()
                    except Exception:
                        logger.warning("quote refresh rollback failed", exc_info=True)
                return RefreshRetryable(target.instrument_id, RetryReason.PERSISTENCE_FAILED)

            if not accepted:
                return RefreshSuccess(target.instrument_id, cache_written=False)

            try:
                await self._cache.set_cached_quote(quote)
            except Exception:
                # The source of truth is committed. A later refresh can repair cache.
                return RefreshSuccess(target.instrument_id, cache_written=False)
            return RefreshSuccess(target.instrument_id, cache_written=True)
        finally:
            try:
                await self._leases.release_refresh_lease(target.instrument_id, owner_token)
            except Exception:
                # Owner-safe release is cleanup only; do not hide the completed outcome.
                logger.warning("quote refresh lease release failed", exc_info=True)

    async def refresh_many(self, targets: Iterable[RefreshTarget]) -> tuple[RefreshResult, ...]:
        return tuple([await self.refresh(target) for target in targets])
