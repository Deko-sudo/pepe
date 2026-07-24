from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.session import require_current_session
from app.core.errors import not_found
from app.db.session import get_db
from app.modules.market_data.domain import AssetClass
from app.modules.market_data.service import get_enabled_instrument_by_slug, list_enabled_instruments
from app.modules.sessions.service import AuthenticatedSession
from app.schemas.assets import AssetCatalogItem, AssetCatalogPage

router = APIRouter(prefix="/assets")


@router.get("", response_model=AssetCatalogPage)
async def list_assets(
    _auth: Annotated[AuthenticatedSession, Depends(require_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    after: str | None = None,
    asset_class: AssetClass | None = None,
) -> AssetCatalogPage:
    instruments, next_cursor = await list_enabled_instruments(
        db,
        limit=limit,
        after=after,
        asset_class=asset_class,
    )
    return AssetCatalogPage(
        items=[AssetCatalogItem.model_validate(instrument) for instrument in instruments],
        next_cursor=next_cursor,
    )


@router.get("/{slug}", response_model=AssetCatalogItem)
async def get_asset(
    slug: str,
    _auth: Annotated[AuthenticatedSession, Depends(require_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssetCatalogItem:
    instrument = await get_enabled_instrument_by_slug(db, slug)
    if instrument is None:
        raise not_found("Asset not found")
    return AssetCatalogItem.model_validate(instrument)
