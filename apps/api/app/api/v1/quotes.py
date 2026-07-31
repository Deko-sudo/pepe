from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pepe_quote_core import has_machine_readable_market_data
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.session import require_current_session
from app.core.config import settings
from app.core.market_data import unavailable_market_data_error
from app.db.session import get_db
from app.modules.market_data.quotes import CurrentQuoteService, get_current_quote_by_slug
from app.modules.sessions.service import AuthenticatedSession
from app.schemas.quotes import CurrentQuoteBatchResponse, CurrentQuoteResponse

router = APIRouter(prefix="/assets")
_CACHE_CONTROL = {"Cache-Control": "private, no-store"}


@router.get("/quotes", response_model=CurrentQuoteBatchResponse)
async def get_current_quotes(
    slugs: Annotated[list[str], Query(alias="slug")],
    _auth: Annotated[AuthenticatedSession, Depends(require_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    if not has_machine_readable_market_data(settings.market_data_mode):
        return JSONResponse(
            status_code=409,
            content=unavailable_market_data_error(settings.market_data_mode, "quotes"),
            headers=_CACHE_CONTROL,
        )
    unique_slugs = sorted(set(slugs))
    if len(unique_slugs) > settings.quote_api_batch_limit:
        return JSONResponse(
            status_code=422,
            content={
                "detail": f"At most {settings.quote_api_batch_limit} unique slugs may be requested",
            },
            headers=_CACHE_CONTROL,
        )
    items: list[CurrentQuoteResponse] = []
    unavailable: list[str] = []
    not_found: list[str] = []
    service = CurrentQuoteService()
    try:
        for slug in unique_slugs:
            resolution = await service.resolve_current_quote_by_slug(db, slug)
            if resolution.quote is not None:
                items.append(resolution.quote)
            elif resolution.not_found:
                not_found.append(slug)
            else:
                unavailable.append(slug)
    finally:
        await service.close()
    return JSONResponse(
        content=CurrentQuoteBatchResponse(
            items=items,
            unavailable=unavailable,
            not_found=not_found,
        ).model_dump(mode="json"),
        headers=_CACHE_CONTROL,
    )


@router.get("/{slug}/quote", response_model=CurrentQuoteResponse)
async def get_current_quote(
    slug: str,
    _auth: Annotated[AuthenticatedSession, Depends(require_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    if not has_machine_readable_market_data(settings.market_data_mode):
        return JSONResponse(
            status_code=409,
            content=unavailable_market_data_error(settings.market_data_mode, "quotes"),
            headers=_CACHE_CONTROL,
        )
    quote = await get_current_quote_by_slug(db, slug)
    if quote is None:
        raise HTTPException(
            status_code=503,
            detail="Current quote is unavailable",
            headers=_CACHE_CONTROL,
        )
    return JSONResponse(content=quote.model_dump(mode="json"), headers=_CACHE_CONTROL)
