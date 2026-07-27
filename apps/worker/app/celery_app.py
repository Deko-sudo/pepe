from celery import Celery

from app.config import worker_settings

celery_app = Celery(
    "pepe_worker",
    broker=worker_settings.redis_url,
    backend=worker_settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_hijack_root_logger=False,
    task_routes={
        "quote.refresh": {"queue": worker_settings.quote_queue_name},
        "candles.sync": {"queue": worker_settings.candle_queue_name},
    },
    beat_schedule={
        "refresh-fake-current-quotes": {
            "task": "quote.refresh",
            "schedule": worker_settings.quote_scheduler_interval_seconds,
        },
        "sync-fake-historical-candles": {
            "task": "candles.sync",
            "schedule": worker_settings.candle_scheduler_interval_seconds,
        },
    },
)

celery_app.autodiscover_tasks(["app"])
