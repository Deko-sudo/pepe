import logging

import asyncpg
from redis.exceptions import RedisError

from app.candle_sync import run_sync_fake_candles
from app.celery_app import celery_app
from app.quote_refresh import run_refresh_fake_quotes

logger = logging.getLogger(__name__)


@celery_app.task(name="heartbeat")
def heartbeat() -> dict[str, str]:
    logger.info("Heartbeat task executed")
    return {
        "service": "pepe-worker",
        "event": "heartbeat",
        "status": "ok",
    }


@celery_app.task(name="test_task")
def run_test_task(value: str = "test") -> dict[str, str]:
    logger.info("Test task executed with value: %s", value)
    return {
        "service": "pepe-worker",
        "event": "test",
        "status": "ok",
        "value": value,
    }


@celery_app.task(
    name="quote.refresh",
    autoretry_for=(OSError, asyncpg.PostgresError, RedisError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def refresh_quotes() -> dict[str, int | str]:
    return run_refresh_fake_quotes()


@celery_app.task(
    name="candles.sync",
    autoretry_for=(OSError, asyncpg.PostgresError, RedisError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def sync_candles() -> dict[str, int | str]:
    return run_sync_fake_candles()
