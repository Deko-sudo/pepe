from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from app.db.models.user_session import UserSession
from app.modules.sessions.service import is_active_session


def test_user_session_schema_contains_only_approved_metadata() -> None:
    columns = {column.name: column for column in UserSession.__table__.columns}
    constraints = getattr(UserSession.__table__, "constraints", ())

    assert set(columns) == {
        "id",
        "user_id",
        "token_digest",
        "created_at",
        "expires_at",
        "idle_expires_at",
        "last_seen_at",
        "revoked_at",
    }
    assert getattr(columns["token_digest"].type, "length", None) == 64
    assert columns["revoked_at"].nullable is True
    assert not {"ip_address", "user_agent", "device_name", "fingerprint"} & set(columns)
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == {"token_digest"}
        for constraint in constraints
    )
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and next(iter(constraint.elements)).ondelete == "CASCADE"
        for constraint in constraints
    )


def test_active_session_requires_not_revoked_and_both_expiries_in_future() -> None:
    now = datetime(2026, 7, 24, tzinfo=UTC)

    assert is_active_session(
        revoked_at=None,
        expires_at=now + timedelta(seconds=1),
        idle_expires_at=now + timedelta(seconds=1),
        now=now,
    )
    assert not is_active_session(
        revoked_at=now,
        expires_at=now + timedelta(seconds=1),
        idle_expires_at=now + timedelta(seconds=1),
        now=now,
    )
    assert not is_active_session(
        revoked_at=None,
        expires_at=now,
        idle_expires_at=now + timedelta(seconds=1),
        now=now,
    )
    assert not is_active_session(
        revoked_at=None,
        expires_at=now + timedelta(seconds=1),
        idle_expires_at=now,
        now=now,
    )
