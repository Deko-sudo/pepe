"""add durable latest market quotes

Revision ID: 005
Revises: 004
Create Date: 2026-07-25 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "latest_market_quotes",
        sa.Column("instrument_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_mapping_id", UUID(as_uuid=True), nullable=False),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("provider_instrument_id", sa.String(128), nullable=True),
        sa.Column("source_venue", sa.String(128), nullable=True),
        sa.Column("market_type", sa.String(32), nullable=False),
        sa.Column("price_type", sa.String(32), nullable=False),
        sa.Column("price", sa.Numeric(38, 18), nullable=False),
        sa.Column("bid", sa.Numeric(38, 18), nullable=True),
        sa.Column("ask", sa.Numeric(38, 18), nullable=True),
        sa.Column("mid", sa.Numeric(38, 18), nullable=True),
        sa.Column("open_24h", sa.Numeric(38, 18), nullable=True),
        sa.Column("high_24h", sa.Numeric(38, 18), nullable=True),
        sa.Column("low_24h", sa.Numeric(38, 18), nullable=True),
        sa.Column("change_24h", sa.Numeric(38, 18), nullable=True),
        sa.Column("change_percent_24h", sa.Numeric(38, 18), nullable=True),
        sa.Column("base_volume_24h", sa.Numeric(38, 18), nullable=True),
        sa.Column("quote_volume_24h", sa.Numeric(38, 18), nullable=True),
        sa.Column("provider_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_delay_seconds", sa.Integer(), nullable=False),
        sa.Column("market_status", sa.String(32), nullable=False),
        sa.Column("delay_class", sa.String(32), nullable=False),
        sa.Column("mapping_version", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("provider_event_id", sa.String(256), nullable=True),
        sa.ForeignKeyConstraint(["instrument_id"], ["asset_instruments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["provider_mapping_id"],
            ["provider_instrument_mappings.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("price > 0", name="ck_latest_quotes_price_positive"),
        sa.CheckConstraint("bid IS NULL OR bid > 0", name="ck_latest_quotes_bid_positive"),
        sa.CheckConstraint("ask IS NULL OR ask > 0", name="ck_latest_quotes_ask_positive"),
        sa.CheckConstraint(
            "bid IS NULL OR ask IS NULL OR bid <= ask",
            name="ck_latest_quotes_bid_lte_ask",
        ),
        sa.CheckConstraint(
            "base_volume_24h IS NULL OR base_volume_24h >= 0",
            name="ck_latest_quotes_base_volume_nonnegative",
        ),
        sa.CheckConstraint(
            "quote_volume_24h IS NULL OR quote_volume_24h >= 0",
            name="ck_latest_quotes_quote_volume_nonnegative",
        ),
        sa.CheckConstraint(
            "low_24h IS NULL OR high_24h IS NULL OR low_24h <= high_24h",
            name="ck_latest_quotes_low_lte_high",
        ),
        sa.CheckConstraint("mapping_version > 0", name="ck_latest_quotes_mapping_version_positive"),
        sa.CheckConstraint("schema_version > 0", name="ck_latest_quotes_schema_version_positive"),
        sa.CheckConstraint(
            "data_delay_seconds >= 0",
            name="ck_latest_quotes_data_delay_nonnegative",
        ),
    )


def downgrade() -> None:
    op.drop_table("latest_market_quotes")
