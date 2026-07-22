import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "pepe-api"}


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    deps: dict[str, str] = {}

    try:
        await db.execute(text("SELECT 1"))
        deps["postgres"] = "ok"
    except Exception:
        deps["postgres"] = "error"

    try:
        redis = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await redis.ping()
        await redis.aclose()
        deps["redis"] = "ok"
    except Exception:
        deps["redis"] = "error"

    all_ok = all(v == "ok" for v in deps.values())

    return {
        "status": "ready" if all_ok else "degraded",
        "service": "pepe-api",
        "dependencies": deps,
    }


@router.get("/version")
async def version() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "service": "pepe-api",
        "version": settings.version,
        "environment": settings.environment,
    }
