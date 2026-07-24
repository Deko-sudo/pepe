"""add asset catalog and provider abstraction

Revision ID: 004
Revises: 003
Create Date: 2026-07-24 00:00:00.000000
"""

# ruff: noqa: E501, COM812

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BTC_USDT_ID = uuid.UUID("a6d8c260-3f98-4d19-9e87-8dd33413b401")
ETH_USDT_ID = uuid.UUID("32cad99d-7cd7-4c7e-9e11-692d84984d02")
XAU_USD_ID = uuid.UUID("d3894b52-0d06-4ce6-934a-e0457e466803")


def upgrade() -> None:
    op.create_table(
        "asset_instruments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("asset_class", sa.String(32), nullable=False),
        sa.Column("market_type", sa.String(32), nullable=False),
        sa.Column("base_asset", sa.String(16), nullable=True),
        sa.Column("quote_asset", sa.String(16), nullable=True),
        sa.Column("price_precision", sa.SmallInteger(), nullable=False),
        sa.Column("quantity_precision", sa.SmallInteger(), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("calendar_kind", sa.String(32), nullable=False),
        sa.Column("trading_calendar", sa.String(64), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("slug", name="uq_asset_instruments_slug"),
        sa.CheckConstraint(
            "asset_class IN ('crypto_spot', 'metal_fx_spot', 'equity_index', 'currency_index', 'government_yield')",
            name="ck_asset_instruments_asset_class",
        ),
        sa.CheckConstraint(
            "market_type IN ('spot', 'reference_index', 'yield_reference')",
            name="ck_asset_instruments_market_type",
        ),
        sa.CheckConstraint(
            "calendar_kind IN ('always_open', 'provider_session', 'exchange', 'reference_data')",
            name="ck_asset_instruments_calendar_kind",
        ),
        sa.CheckConstraint(
            "price_precision >= 0 AND price_precision <= 12",
            name="ck_asset_instruments_price_precision",
        ),
        sa.CheckConstraint(
            "quantity_precision IS NULL OR (quantity_precision >= 0 AND quantity_precision <= 12)",
            name="ck_asset_instruments_quantity_precision",
        ),
        sa.CheckConstraint(
            "metadata_version > 0", name="ck_asset_instruments_metadata_version_positive"
        ),
    )
    op.create_index(
        "ix_asset_instruments_enabled_slug", "asset_instruments", ["is_enabled", "slug"]
    )
    op.create_index(
        "ix_asset_instruments_enabled_class_slug",
        "asset_instruments",
        ["is_enabled", "asset_class", "slug"],
    )
    op.create_table(
        "provider_instrument_mappings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("instrument_id", UUID(as_uuid=True), nullable=False),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("provider_symbol", sa.String(128), nullable=False),
        sa.Column("provider_market", sa.String(64), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority", sa.SmallInteger(), nullable=False),
        sa.Column("mapping_version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["instrument_id"], ["asset_instruments.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "instrument_id", "provider_key", name="uq_provider_mapping_instrument_provider"
        ),
        sa.UniqueConstraint(
            "provider_key",
            "provider_market",
            "provider_symbol",
            name="uq_provider_mapping_provider_symbol",
        ),
        sa.CheckConstraint("priority > 0", name="ck_provider_mapping_priority_positive"),
        sa.CheckConstraint("mapping_version > 0", name="ck_provider_mapping_version_positive"),
    )
    op.create_index(
        "ix_provider_mapping_instrument_id", "provider_instrument_mappings", ["instrument_id"]
    )
    op.create_index(
        "ix_provider_mapping_provider_lookup",
        "provider_instrument_mappings",
        ["provider_key", "provider_market", "provider_symbol"],
    )
    op.create_index(
        "uq_provider_mapping_enabled_priority",
        "provider_instrument_mappings",
        ["instrument_id", "priority"],
        unique=True,
        postgresql_where=sa.text("is_enabled"),
    )
    instruments = sa.table(
        "asset_instruments",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("slug", sa.String()),
        sa.column("symbol", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("asset_class", sa.String()),
        sa.column("market_type", sa.String()),
        sa.column("base_asset", sa.String()),
        sa.column("quote_asset", sa.String()),
        sa.column("price_precision", sa.SmallInteger()),
        sa.column("quantity_precision", sa.SmallInteger()),
        sa.column("timezone", sa.String()),
        sa.column("calendar_kind", sa.String()),
        sa.column("trading_calendar", sa.String()),
        sa.column("is_enabled", sa.Boolean()),
        sa.column("metadata_version", sa.Integer()),
    )
    op.bulk_insert(
        instruments,
        [
            {
                "id": BTC_USDT_ID,
                "slug": "btc-usdt",
                "symbol": "BTC/USDT",
                "display_name": "Bitcoin / Tether",
                "asset_class": "crypto_spot",
                "market_type": "spot",
                "base_asset": "BTC",
                "quote_asset": "USDT",
                "price_precision": 2,
                "quantity_precision": 8,
                "timezone": "UTC",
                "calendar_kind": "always_open",
                "trading_calendar": "crypto-24x7",
                "is_enabled": True,
                "metadata_version": 1,
            },
            {
                "id": ETH_USDT_ID,
                "slug": "eth-usdt",
                "symbol": "ETH/USDT",
                "display_name": "Ethereum / Tether",
                "asset_class": "crypto_spot",
                "market_type": "spot",
                "base_asset": "ETH",
                "quote_asset": "USDT",
                "price_precision": 2,
                "quantity_precision": 8,
                "timezone": "UTC",
                "calendar_kind": "always_open",
                "trading_calendar": "crypto-24x7",
                "is_enabled": True,
                "metadata_version": 1,
            },
            {
                "id": XAU_USD_ID,
                "slug": "xau-usd",
                "symbol": "XAU/USD",
                "display_name": "Gold / US Dollar",
                "asset_class": "metal_fx_spot",
                "market_type": "spot",
                "base_asset": "XAU",
                "quote_asset": "USD",
                "price_precision": 2,
                "quantity_precision": None,
                "timezone": "UTC",
                "calendar_kind": "provider_session",
                "trading_calendar": "xau-usd-provider-session",
                "is_enabled": True,
                "metadata_version": 1,
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM provider_instrument_mappings")
    op.execute("DELETE FROM asset_instruments")
    op.drop_index("uq_provider_mapping_enabled_priority", table_name="provider_instrument_mappings")
    op.drop_index("ix_provider_mapping_provider_lookup", table_name="provider_instrument_mappings")
    op.drop_index("ix_provider_mapping_instrument_id", table_name="provider_instrument_mappings")
    op.drop_table("provider_instrument_mappings")
    op.drop_index("ix_asset_instruments_enabled_class_slug", table_name="asset_instruments")
    op.drop_index("ix_asset_instruments_enabled_slug", table_name="asset_instruments")
    op.drop_table("asset_instruments")
