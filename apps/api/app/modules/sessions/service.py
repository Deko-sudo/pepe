from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.models.user_session import UserSession

SESSION_TOKEN_BYTES = 32


@dataclass(frozen=True)
class AuthenticatedSession:
    user: User
    session: UserSession


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_session_token() -> str:
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def digest_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def clamp_idle_expiry(
    *,
    now: datetime,
    absolute_expiry: datetime,
    idle_ttl_seconds: int,
) -> datetime:
    return min(now + timedelta(seconds=idle_ttl_seconds), absolute_expiry)


def is_active_session(
    *,
    revoked_at: datetime | None,
    expires_at: datetime,
    idle_expires_at: datetime,
    now: datetime,
) -> bool:
    return revoked_at is None and expires_at > now and idle_expires_at > now


async def get_active_session_by_token(
    db: AsyncSession,
    token: str,
    *,
    now: datetime,
    lock_for_update: bool = False,
) -> UserSession | None:
    statement = select(UserSession).where(UserSession.token_digest == digest_session_token(token))
    if lock_for_update:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    result = await db.execute(statement)
    session = result.scalar_one_or_none()
    if session is None or not is_active_session(
        revoked_at=session.revoked_at,
        expires_at=session.expires_at,
        idle_expires_at=session.idle_expires_at,
        now=now,
    ):
        return None
    return session


async def create_session(
    db: AsyncSession,
    user: User,
    *,
    absolute_ttl_seconds: int,
    idle_ttl_seconds: int,
    max_active_sessions: int,
    now: datetime,
) -> tuple[UserSession, str]:
    await db.execute(select(User.id).where(User.id == user.id).with_for_update())
    active_statement = (
        select(UserSession)
        .where(
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
            UserSession.idle_expires_at > now,
        )
        .order_by(UserSession.created_at.asc(), UserSession.id.asc())
    )
    active_result = await db.execute(active_statement)
    active_sessions = list(active_result.scalars().all())
    sessions_to_revoke = max(0, len(active_sessions) - (max_active_sessions - 1))
    for old_session in active_sessions[:sessions_to_revoke]:
        old_session.revoked_at = now

    expires_at = now + timedelta(seconds=absolute_ttl_seconds)
    session = UserSession(
        user_id=user.id,
        token_digest=digest_session_token(token := generate_session_token()),
        expires_at=expires_at,
        idle_expires_at=clamp_idle_expiry(
            now=now,
            absolute_expiry=expires_at,
            idle_ttl_seconds=idle_ttl_seconds,
        ),
        last_seen_at=now,
    )
    db.add(session)
    await db.flush()
    return session, token


async def revoke_presented_session(
    db: AsyncSession,
    token: str | None,
    *,
    now: datetime,
) -> None:
    if not token:
        return
    session = await get_active_session_by_token(db, token, now=now)
    if session is not None:
        session.revoked_at = now


async def resolve_authenticated_session(
    db: AsyncSession,
    token: str | None,
    *,
    idle_ttl_seconds: int,
    now: datetime,
) -> AuthenticatedSession | None:
    if not token:
        return None
    session = await get_active_session_by_token(db, token, now=now)
    if session is None:
        return None

    await db.execute(select(User.id).where(User.id == session.user_id).with_for_update())
    session = await get_active_session_by_token(db, token, now=now, lock_for_update=True)
    if session is None:
        return None

    user = await db.get(User, session.user_id)
    if user is None:
        return None
    session.last_seen_at = max(session.last_seen_at, now)
    candidate_idle_expiry = clamp_idle_expiry(
        now=now,
        absolute_expiry=session.expires_at,
        idle_ttl_seconds=idle_ttl_seconds,
    )
    session.idle_expires_at = min(
        max(session.idle_expires_at, candidate_idle_expiry),
        session.expires_at,
    )
    return AuthenticatedSession(user=user, session=session)


async def revoke_all_active_sessions(
    db: AsyncSession,
    user_id: object,
    *,
    now: datetime,
) -> None:
    await db.execute(select(User.id).where(User.id == user_id).with_for_update())
    statement = select(UserSession).where(
        UserSession.user_id == user_id,
        UserSession.revoked_at.is_(None),
        UserSession.expires_at > now,
        UserSession.idle_expires_at > now,
    )
    result = await db.execute(statement)
    for session in result.scalars().all():
        session.revoked_at = now
