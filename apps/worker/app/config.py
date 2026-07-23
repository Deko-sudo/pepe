from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}


worker_settings = WorkerSettings()
