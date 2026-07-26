"""add market candles

Revision ID: 007
Revises: 006
Create Date: 2026-07-26
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_candles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "instrument_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asset_instruments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(38, 18), nullable=False),
        sa.Column("high", sa.Numeric(38, 18), nullable=False),
        sa.Column("low", sa.Numeric(38, 18), nullable=False),
        sa.Column("close", sa.Numeric(38, 18), nullable=False),
        sa.Column("base_volume", sa.Numeric(38, 18)),
        sa.Column("quote_volume", sa.Numeric(38, 18)),
        sa.Column("trade_count", sa.Integer()),
        sa.Column("source_label", sa.String(length=128), nullable=False),
        sa.Column("venue_label", sa.String(length=128)),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "instrument_id", "timeframe", "open_time", name="uq_market_candles_identity",
        ),
        sa.CheckConstraint("close_time > open_time", name="ck_market_candles_positive_interval"),
        sa.CheckConstraint(
            "open > 0 AND high > 0 AND low > 0 AND close > 0",
            name="ck_market_candles_ohlc_positive",
        ),
        sa.CheckConstraint(
            "high >= open AND high >= close AND high >= low", name="ck_market_candles_high_bounds",
        ),
        sa.CheckConstraint("low <= open AND low <= close", name="ck_market_candles_low_bounds"),
        sa.CheckConstraint(
            "base_volume IS NULL OR base_volume >= 0",
            name="ck_market_candles_base_volume_nonnegative",
        ),
        sa.CheckConstraint(
            "quote_volume IS NULL OR quote_volume >= 0",
            name="ck_market_candles_quote_volume_nonnegative",
        ),
        sa.CheckConstraint(
            "trade_count IS NULL OR trade_count >= 0",
            name="ck_market_candles_trade_count_nonnegative",
        ),
    )
    op.create_index(
        "ix_market_candles_instrument_timeframe_open",
        "market_candles",
        ["instrument_id", "timeframe", "open_time"],
    )


def downgrade() -> None:
    op.drop_index("ix_market_candles_instrument_timeframe_open", table_name="market_candles")
    op.drop_table("market_candles")
