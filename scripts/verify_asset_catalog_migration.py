#!/usr/bin/env python3
"""Verify the deterministic Stage-5 catalog after Alembic upgrades."""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text

from app.db.session import engine

EXPECTED_ASSETS = [
    (
        "a6d8c260-3f98-4d19-9e87-8dd33413b401",
        "btc-usdt",
        "BTC/USDT",
        "Bitcoin / Tether",
        "crypto_spot",
        "spot",
        "BTC",
        "USDT",
        2,
        8,
        "UTC",
        "always_open",
        "crypto-24x7",
        True,
        1,
    ),
    (
        "32cad99d-7cd7-4c7e-9e11-692d84984d02",
        "eth-usdt",
        "ETH/USDT",
        "Ethereum / Tether",
        "crypto_spot",
        "spot",
        "ETH",
        "USDT",
        2,
        8,
        "UTC",
        "always_open",
        "crypto-24x7",
        True,
        1,
    ),
    (
        "d3894b52-0d06-4ce6-934a-e0457e466803",
        "xau-usd",
        "XAU/USD",
        "Gold / US Dollar",
        "metal_fx_spot",
        "spot",
        "XAU",
        "USD",
        2,
        None,
        "UTC",
        "provider_session",
        "xau-usd-provider-session",
        True,
        1,
    ),
]


async def verify(expect_absent: bool = False) -> None:
    async with engine.connect() as connection:
        if expect_absent:
            asset_table = await connection.scalar(text("SELECT to_regclass('asset_instruments')"))
            mapping_table = await connection.scalar(text("SELECT to_regclass('provider_instrument_mappings')"))
            if asset_table is not None or mapping_table is not None:
                raise AssertionError("asset catalog tables must be absent after downgrade")
            return
        assets = (
            await connection.execute(
                text(
                    "SELECT id::text, slug, symbol, display_name, asset_class, market_type, "
                    "base_asset, quote_asset, price_precision, quantity_precision, timezone, "
                    "calendar_kind, trading_calendar, is_enabled, metadata_version "
                    "FROM asset_instruments ORDER BY slug",
                ),
            )
        ).all()
        mapping_count = await connection.scalar(text("SELECT count(*) FROM provider_instrument_mappings"))

    expected_by_slug = sorted(EXPECTED_ASSETS, key=lambda asset: asset[1])
    if assets != expected_by_slug:
        raise AssertionError(f"unexpected deterministic catalog seed: {assets!r}")
    if mapping_count != 0:
        raise AssertionError("initial catalog must not seed provider mappings")


if __name__ == "__main__":
    expect_absent = sys.argv[1:] == ["--absent"]
    asyncio.run(verify(expect_absent))
    print("ASSET_CATALOG_MIGRATION_ABSENT_PASS" if expect_absent else "ASSET_CATALOG_MIGRATION_VERIFY_PASS")
