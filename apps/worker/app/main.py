import logging
import signal
import sys

from app.celery_app import celery_app
from app.config import worker_settings

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


def handle_signal(signum: int, frame: object) -> None:
    logger.info("Received signal %s, shutting down gracefully...", signum)


def main() -> None:
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logger.info("Starting Pepe worker...")
    logger.info("Redis URL configured: %s", "yes" if worker_settings.redis_url else "no")

    celery_app.worker_main(
        [
            "worker",
            "--loglevel=info",
            "--concurrency=2",
        ],
    )


if __name__ == "__main__":
    main()
