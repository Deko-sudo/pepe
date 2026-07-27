from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pepe_quote_core import CandleTimeframe
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.session import require_current_session
from app.db.session import get_db
from app.modules.market_data.candles import HistoricalCandleService
from app.modules.sessions.service import AuthenticatedSession
from app.schemas.candles import CandlesResponse

router = APIRouter(prefix="/market-data/instruments")
_CACHE_CONTROL = {"Cache-Control": "private, no-store"}


@router.get("/{slug}/candles", response_model=CandlesResponse)
async def get_candles(
    slug: str,
    timeframe: CandleTimeframe,
    _auth: Annotated[AuthenticatedSession, Depends(require_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
) -> JSONResponse:
    if (from_time is not None and from_time.tzinfo is None) or (
        to_time is not None and to_time.tzinfo is None
    ):
        raise HTTPException(
            status_code=422,
            detail="range timestamps must be timezone-aware UTC",
            headers=_CACHE_CONTROL,
        )
    from_time = from_time.astimezone(UTC) if from_time is not None else None
    to_time = to_time.astimezone(UTC) if to_time is not None else None
    try:
        result = await HistoricalCandleService().resolve(
            db,
            slug=slug,
            timeframe=timeframe,
            from_time=from_time,
            to_time=to_time,
            limit=limit,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error), headers=_CACHE_CONTROL) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Asset not found", headers=_CACHE_CONTROL)
    return JSONResponse(content=result.model_dump(mode="json"), headers=_CACHE_CONTROL)
