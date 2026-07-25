from pydantic import Field
from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    quote_cache_url: str = "redis://localhost:6379/1"
    quote_cache_namespace: str = "pepe:quotes:v1"
    quote_cache_ttl_seconds: int = Field(default=60, gt=0)
    quote_refresh_lease_ttl_seconds: int = Field(default=120, gt=0)
    database_url: str = "postgresql+asyncpg://pepe:change_me@localhost:5432/pepe"
    quote_queue_name: str = "quotes"
    quote_fake_provider_enabled: bool = False
    quote_scheduler_interval_seconds: int = 60
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}


worker_settings = WorkerSettings()
