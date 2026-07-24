from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.asset_instrument import AssetInstrument
from app.db.models.provider_instrument_mapping import ProviderInstrumentMapping
from app.modules.market_data.domain import AssetClass
from app.modules.market_data.errors import InstrumentNotMapped
from app.modules.market_data.providers import ProviderMapping, ProviderSelection, select_mapping


async def list_enabled_instruments(
    db: AsyncSession,
    *,
    limit: int,
    after: str | None,
    asset_class: AssetClass | None,
) -> tuple[list[AssetInstrument], str | None]:
    statement = select(AssetInstrument).where(AssetInstrument.is_enabled.is_(True))
    if after is not None:
        statement = statement.where(AssetInstrument.slug > after)
    if asset_class is not None:
        statement = statement.where(AssetInstrument.asset_class == asset_class.value)
    statement = statement.order_by(AssetInstrument.slug).limit(limit + 1)
    result = await db.execute(statement)
    instruments = list(result.scalars())
    has_more = len(instruments) > limit
    page = instruments[:limit]
    return page, page[-1].slug if has_more else None


async def get_enabled_instrument_by_slug(
    db: AsyncSession,
    slug: str,
) -> AssetInstrument | None:
    statement = select(AssetInstrument).where(
        AssetInstrument.slug == slug,
        AssetInstrument.is_enabled.is_(True),
    )
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def select_enabled_mapping(
    db: AsyncSession,
    instrument_id: uuid.UUID,
) -> ProviderSelection:
    statement = (
        select(ProviderInstrumentMapping)
        .where(
            ProviderInstrumentMapping.instrument_id == instrument_id,
            ProviderInstrumentMapping.is_enabled.is_(True),
        )
        .order_by(ProviderInstrumentMapping.priority, ProviderInstrumentMapping.provider_key)
        .limit(1)
    )
    result = await db.execute(statement)
    mapping = result.scalar_one_or_none()
    if mapping is None:
        raise InstrumentNotMapped()
    return select_mapping(
        instrument_id,
        [
            ProviderMapping(
                instrument_id=mapping.instrument_id,
                provider_key=mapping.provider_key,
                provider_symbol=mapping.provider_symbol,
                provider_market=mapping.provider_market,
                priority=mapping.priority,
                is_enabled=mapping.is_enabled,
                mapping_version=mapping.mapping_version,
            ),
        ],
    )
