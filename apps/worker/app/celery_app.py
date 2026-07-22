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
)

celery_app.autodiscover_tasks(["app"])
