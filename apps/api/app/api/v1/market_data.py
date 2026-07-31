from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies.session import require_current_session
from app.core.config import settings
from app.core.market_data import capabilities_for
from app.modules.sessions.service import AuthenticatedSession

router = APIRouter(prefix="/market-data")
_CACHE_CONTROL = {"Cache-Control": "private, no-store"}


@router.get("/capabilities")
async def get_market_data_capabilities(
    _auth: Annotated[AuthenticatedSession, Depends(require_current_session)],
) -> JSONResponse:
    return JSONResponse(
        content=capabilities_for(settings.market_data_mode).model_dump(mode="json"),
        headers=_CACHE_CONTROL,
    )
