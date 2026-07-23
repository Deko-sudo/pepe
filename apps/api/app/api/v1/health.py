from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "pepe-api"}


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    deps: dict[str, str] = {}
    redis = None

    try:
        await db.execute(text("SELECT 1"))
        deps["postgres"] = "ok"
    except Exception:
        deps["postgres"] = "error"

    try:
        import redis.asyncio as aioredis

        redis = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await redis.ping()
        deps["redis"] = "ok"
    except Exception:
        deps["redis"] = "error"
    finally:
        if redis is not None:
            await redis.aclose()

    all_ok = all(v == "ok" for v in deps.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        content={
            "status": "ready" if all_ok else "degraded",
            "service": "pepe-api",
            "dependencies": deps,
        },
        status_code=status_code,
    )


@router.get("/version")
async def version() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "service": "pepe-api",
        "version": settings.version,
        "environment": settings.environment,
    }
