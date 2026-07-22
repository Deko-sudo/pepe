import logging

from app.celery_app import celery_app

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
def test_task(value: str = "test") -> dict[str, str]:
    logger.info("Test task executed with value: %s", value)
    return {
        "service": "pepe-worker",
        "event": "test",
        "status": "ok",
        "value": value,
    }
