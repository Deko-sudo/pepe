from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import suppress
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, event, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.models.user import User
from app.db.models.user_session import UserSession
from app.modules.sessions.service import (
    AuthenticatedSession,
    create_session,
    digest_session_token,
    is_active_session,
    resolve_authenticated_session,
    revoke_all_active_sessions,
    revoke_presented_session,
)

pytestmark = pytest.mark.skipif(
    os.getenv("PEPE_RUN_POSTGRES_INTEGRATION") != "1",
    reason="requires PEPE_RUN_POSTGRES_INTEGRATION=1 and a disposable PostgreSQL database",
)


@pytest.fixture
async def postgres_sessions() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url or not database_url.startswith("postgresql+asyncpg://"):
        pytest.fail("PostgreSQL integration tests require a postgresql+asyncpg DATABASE_URL")

    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    finally:
        await engine.dispose()


async def create_test_user(postgres_sessions: async_sessionmaker[AsyncSession]) -> uuid.UUID:
    async with postgres_sessions() as db:
        user = User(
            telegram_id=uuid.uuid4().int % 9_000_000_000_000_000_000,
            first_name="PostgreSQL session test",
        )
        db.add(user)
        await db.commit()
        return user.id


async def delete_test_user(
    postgres_sessions: async_sessionmaker[AsyncSession],
    user_id: uuid.UUID,
) -> None:
    async with postgres_sessions() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def create_committed_session(
    postgres_sessions: async_sessionmaker[AsyncSession],
    user_id: uuid.UUID,
    *,
    now: datetime,
) -> tuple[uuid.UUID, str]:
    async with postgres_sessions() as db:
        user = await db.get(User, user_id)
        assert user is not None
        session, token = await create_session(
            db,
            user,
            absolute_ttl_seconds=2_592_000,
            idle_ttl_seconds=604_800,
            max_active_sessions=5,
            now=now,
        )
        await db.commit()
        return session.id, token


@pytest.mark.asyncio
async def test_logout_all_waits_for_create_session_user_lock(
    postgres_sessions: async_sessionmaker[AsyncSession],
) -> None:
    user_id = await create_test_user(postgres_sessions)
    creation_has_user_lock = asyncio.Event()
    allow_creation_commit = asyncio.Event()
    logout_started = asyncio.Event()
    now = datetime.now(UTC)

    async def create_while_holding_user_lock() -> None:
        async with postgres_sessions() as db:
            user = await db.get(User, user_id)
            assert user is not None
            await create_session(
                db,
                user,
                absolute_ttl_seconds=2_592_000,
                idle_ttl_seconds=604_800,
                max_active_sessions=5,
                now=now,
            )
            creation_has_user_lock.set()
            await allow_creation_commit.wait()
            await db.commit()

    async def logout_all() -> None:
        await creation_has_user_lock.wait()
        async with postgres_sessions() as db:
            logout_started.set()
            await revoke_all_active_sessions(db, user_id, now=now + timedelta(seconds=1))
            await db.commit()

    creation_task = asyncio.create_task(create_while_holding_user_lock())
    logout_task = asyncio.create_task(logout_all())
    try:
        await asyncio.wait_for(logout_started.wait(), timeout=2)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(asyncio.shield(logout_task), timeout=0.2)

        allow_creation_commit.set()
        await asyncio.wait_for(creation_task, timeout=2)
        await asyncio.wait_for(logout_task, timeout=2)

        async with postgres_sessions() as db:
            result = await db.execute(select(UserSession).where(UserSession.user_id == user_id))
            sessions = list(result.scalars())

        assert len(sessions) == 1
        assert sessions[0].revoked_at == now + timedelta(seconds=1)
        assert not is_active_session(
            revoked_at=sessions[0].revoked_at,
            expires_at=sessions[0].expires_at,
            idle_expires_at=sessions[0].idle_expires_at,
            now=now + timedelta(seconds=1),
        )
    finally:
        allow_creation_commit.set()
        if not creation_task.done():
            await asyncio.wait_for(creation_task, timeout=2)
        if not logout_task.done():
            await asyncio.wait_for(logout_task, timeout=2)
        await delete_test_user(postgres_sessions, user_id)


@pytest.mark.asyncio
async def test_authenticated_session_locks_user_before_presented_session(
    postgres_sessions: async_sessionmaker[AsyncSession],
) -> None:
    user_id = await create_test_user(postgres_sessions)
    now = datetime.now(UTC)
    _, token = await create_committed_session(postgres_sessions, user_id, now=now)
    resolution_task: asyncio.Task[None] | None = None

    try:
        async with postgres_sessions() as locking_db:
            await locking_db.execute(select(User.id).where(User.id == user_id).with_for_update())

            async def resolve_while_user_is_locked() -> None:
                async with postgres_sessions() as db:
                    authenticated = await resolve_authenticated_session(
                        db,
                        token,
                        idle_ttl_seconds=604_800,
                        now=now + timedelta(seconds=1),
                    )
                    assert authenticated is not None
                    await db.commit()

            resolution_task = asyncio.create_task(resolve_while_user_is_locked())
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(resolution_task), timeout=0.2)

            async with postgres_sessions() as probe_db:
                await probe_db.execute(
                    select(UserSession.id)
                    .where(UserSession.token_digest == digest_session_token(token))
                    .with_for_update(nowait=True),
                )

            await locking_db.commit()

        await asyncio.wait_for(resolution_task, timeout=2)
    finally:
        if resolution_task is not None and not resolution_task.done():
            resolution_task.cancel()
            with suppress(asyncio.CancelledError):
                await resolution_task
        await delete_test_user(postgres_sessions, user_id)


@pytest.mark.asyncio
async def test_authenticated_session_revalidates_after_concurrent_logout(
    postgres_sessions: async_sessionmaker[AsyncSession],
) -> None:
    user_id = await create_test_user(postgres_sessions)
    now = datetime.now(UTC)
    _, token = await create_committed_session(postgres_sessions, user_id, now=now)
    initial_lookup_completed = asyncio.Event()
    resolver_task: asyncio.Task[None] | None = None
    resolution_result: list[AuthenticatedSession | None] = []
    engine = postgres_sessions.kw["bind"]
    assert isinstance(engine, AsyncEngine)
    loop = asyncio.get_running_loop()

    def record_initial_session_lookup(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: object,
    ) -> None:
        if "FROM user_sessions" in statement and "FOR UPDATE" not in statement:
            loop.call_soon_threadsafe(initial_lookup_completed.set)

    event.listen(engine.sync_engine, "after_cursor_execute", record_initial_session_lookup)
    try:
        async with postgres_sessions() as locking_db:
            await locking_db.execute(select(User.id).where(User.id == user_id).with_for_update())

            async def resolve_while_user_is_locked() -> None:
                async with postgres_sessions() as db:
                    resolution_result.append(
                        await resolve_authenticated_session(
                            db,
                            token,
                            idle_ttl_seconds=604_800,
                            now=now + timedelta(seconds=1),
                        ),
                    )
                    await db.commit()

            resolver_task = asyncio.create_task(resolve_while_user_is_locked())
            await asyncio.wait_for(initial_lookup_completed.wait(), timeout=2)
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(resolver_task), timeout=0.2)

            async with postgres_sessions() as revoking_db:
                await revoke_presented_session(revoking_db, token, now=now + timedelta(seconds=1))
                await revoking_db.commit()

            await locking_db.commit()

        await asyncio.wait_for(resolver_task, timeout=2)
        assert resolution_result == [None]
    finally:
        event.remove(engine.sync_engine, "after_cursor_execute", record_initial_session_lookup)
        if resolver_task is not None and not resolver_task.done():
            resolver_task.cancel()
            with suppress(asyncio.CancelledError):
                await resolver_task
        await delete_test_user(postgres_sessions, user_id)


@pytest.mark.asyncio
async def test_rotation_locks_user_before_flushing_presented_session_revocation(
    postgres_sessions: async_sessionmaker[AsyncSession],
) -> None:
    user_id = await create_test_user(postgres_sessions)
    now = datetime.now(UTC)
    _, token = await create_committed_session(postgres_sessions, user_id, now=now)
    rotation_user_lock_attempted = asyncio.Event()
    rotation_task: asyncio.Task[None] | None = None
    engine = postgres_sessions.kw["bind"]
    assert isinstance(engine, AsyncEngine)
    loop = asyncio.get_running_loop()

    def record_rotation_user_lock_attempt(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: object,
    ) -> None:
        if "FROM users" in statement and "FOR UPDATE" in statement:
            loop.call_soon_threadsafe(rotation_user_lock_attempted.set)

    try:
        async with postgres_sessions() as locking_db:
            await locking_db.execute(select(User.id).where(User.id == user_id).with_for_update())
            event.listen(
                engine.sync_engine,
                "before_cursor_execute",
                record_rotation_user_lock_attempt,
            )

            async def rotate_session() -> None:
                async with postgres_sessions() as db:
                    user = await db.get(User, user_id)
                    assert user is not None
                    await revoke_presented_session(db, token, now=now)
                    await create_session(
                        db,
                        user,
                        absolute_ttl_seconds=2_592_000,
                        idle_ttl_seconds=604_800,
                        max_active_sessions=5,
                        now=now,
                    )
                    await db.commit()

            rotation_task = asyncio.create_task(rotate_session())
            await asyncio.wait_for(rotation_user_lock_attempted.wait(), timeout=2)
            await locking_db.execute(
                select(UserSession.id)
                .where(UserSession.token_digest == digest_session_token(token))
                .with_for_update(nowait=True),
            )
            await locking_db.commit()

        await asyncio.wait_for(rotation_task, timeout=2)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record_rotation_user_lock_attempt)
        if rotation_task is not None and not rotation_task.done():
            rotation_task.cancel()
            with suppress(asyncio.CancelledError):
                await rotation_task
        await delete_test_user(postgres_sessions, user_id)


@pytest.mark.asyncio
async def test_idle_refresh_is_monotonic_when_earlier_request_commits_after_later_request(
    postgres_sessions: async_sessionmaker[AsyncSession],
) -> None:
    user_id = await create_test_user(postgres_sessions)
    base_now = datetime.now(UTC)
    session_id, token = await create_committed_session(postgres_sessions, user_id, now=base_now)
    earlier_request_now = base_now + timedelta(minutes=1)
    later_request_now = base_now + timedelta(minutes=2)
    later_refresh_committed = asyncio.Event()

    async def refresh_later_request() -> None:
        async with postgres_sessions() as db:
            authenticated = await resolve_authenticated_session(
                db,
                token,
                idle_ttl_seconds=604_800,
                now=later_request_now,
            )
            assert authenticated is not None
            await db.commit()
            later_refresh_committed.set()

    async def complete_earlier_request_after_later_refresh() -> None:
        await later_refresh_committed.wait()
        async with postgres_sessions() as db:
            authenticated = await resolve_authenticated_session(
                db,
                token,
                idle_ttl_seconds=604_800,
                now=earlier_request_now,
            )
            assert authenticated is not None
            await db.commit()

    try:
        await asyncio.wait_for(
            asyncio.gather(refresh_later_request(), complete_earlier_request_after_later_refresh()),
            timeout=4,
        )

        async with postgres_sessions() as db:
            session = await db.get(UserSession, session_id)
            assert session is not None

        expected_idle_expiry = later_request_now + timedelta(seconds=604_800)
        assert session.last_seen_at == later_request_now
        assert session.idle_expires_at == expected_idle_expiry
        assert session.idle_expires_at <= session.expires_at
        assert session.expires_at == base_now + timedelta(seconds=2_592_000)
    finally:
        await delete_test_user(postgres_sessions, user_id)
