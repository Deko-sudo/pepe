from fastapi import APIRouter

from app.api.v1.assets import router as assets_router
from app.api.v1.auth import router as auth_router
from app.api.v1.candles import router as candles_router
from app.api.v1.health import router as health_router
from app.api.v1.market_data import router as market_data_router
from app.api.v1.quotes import router as quotes_router
from app.api.v1.users import router as users_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(quotes_router)
api_router.include_router(candles_router)
api_router.include_router(market_data_router)
api_router.include_router(assets_router)
