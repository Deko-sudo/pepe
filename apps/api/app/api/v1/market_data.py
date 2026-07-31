from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.dependencies.session import require_current_session
from app.core.config import settings
from app.core.market_data import (
    capabilities_for,
    embedded_chart_config,
    unavailable_market_data_error,
)
from app.modules.sessions.service import AuthenticatedSession

router = APIRouter(prefix="/market-data")
_CACHE_CONTROL = {"Cache-Control": "private, no-store"}


@router.get("/capabilities")
async def get_market_data_capabilities(
    _auth: Annotated[AuthenticatedSession, Depends(require_current_session)],
) -> JSONResponse:
    return JSONResponse(
        content=capabilities_for(
            settings.market_data_mode,
            provider=settings.embedded_chart_provider,
            enabled=settings.embedded_chart_enabled,
        ).model_dump(mode="json"),
        headers=_CACHE_CONTROL,
    )


@router.get("/embedded-chart-config")
async def get_embedded_chart_config(
    _auth: Annotated[AuthenticatedSession, Depends(require_current_session)],
    slug: Annotated[str, Query(min_length=1, max_length=64)],
    timeframe: Annotated[str, Query(min_length=1, max_length=8)],
) -> JSONResponse:
    capabilities = capabilities_for(
        settings.market_data_mode,
        provider=settings.embedded_chart_provider,
        enabled=settings.embedded_chart_enabled,
    )
    if not capabilities.embedded_chart_available:
        return JSONResponse(
            status_code=409,
            content=unavailable_market_data_error(settings.market_data_mode, "embedded_chart"),
            headers=_CACHE_CONTROL,
        )
    config = embedded_chart_config(slug, timeframe)
    if config is None:
        return JSONResponse(
            status_code=409,
            content=unavailable_market_data_error(settings.market_data_mode, "embedded_chart"),
            headers=_CACHE_CONTROL,
        )
    return JSONResponse(content=config.model_dump(), headers=_CACHE_CONTROL)
