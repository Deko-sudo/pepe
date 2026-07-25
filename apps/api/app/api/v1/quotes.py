from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.session import require_current_session
from app.db.session import get_db
from app.modules.market_data.quotes import get_current_quote_by_slug
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
    unique_slugs = sorted(set(slugs))
    if len(unique_slugs) > 20:
        return JSONResponse(
            status_code=422,
            content={"detail": "At most 20 unique slugs may be requested"},
            headers=_CACHE_CONTROL,
        )
    items: list[CurrentQuoteResponse] = []
    unavailable: list[str] = []
    for slug in unique_slugs:
        quote = await get_current_quote_by_slug(db, slug)
        if quote is None:
            unavailable.append(slug)
        else:
            items.append(quote)
    return JSONResponse(
        content=CurrentQuoteBatchResponse(
            items=items,
            unavailable=unavailable,
            not_found=[],
        ).model_dump(mode="json"),
        headers=_CACHE_CONTROL,
    )


@router.get("/{slug}/quote", response_model=CurrentQuoteResponse)
async def get_current_quote(
    slug: str,
    _auth: Annotated[AuthenticatedSession, Depends(require_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    quote = await get_current_quote_by_slug(db, slug)
    if quote is None:
        raise HTTPException(
            status_code=503,
            detail="Current quote is unavailable",
            headers=_CACHE_CONTROL,
        )
    return JSONResponse(content=quote.model_dump(mode="json"), headers=_CACHE_CONTROL)
