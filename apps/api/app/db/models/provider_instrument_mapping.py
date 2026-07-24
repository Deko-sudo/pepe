from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProviderInstrumentMapping(Base):
    __tablename__ = "provider_instrument_mappings"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "provider_key",
            name="uq_provider_mapping_instrument_provider",
        ),
        UniqueConstraint(
            "provider_key",
            "provider_market",
            "provider_symbol",
            name="uq_provider_mapping_provider_symbol",
        ),
        CheckConstraint("priority > 0", name="ck_provider_mapping_priority_positive"),
        CheckConstraint("mapping_version > 0", name="ck_provider_mapping_version_positive"),
        Index("ix_provider_mapping_instrument_id", "instrument_id"),
        Index(
            "ix_provider_mapping_provider_lookup",
            "provider_key",
            "provider_market",
            "provider_symbol",
        ),
        Index(
            "uq_provider_mapping_enabled_priority",
            "instrument_id",
            "priority",
            unique=True,
            postgresql_where=text("is_enabled"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_instruments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_symbol: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_market: Mapped[str] = mapped_column(String(64), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    mapping_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
