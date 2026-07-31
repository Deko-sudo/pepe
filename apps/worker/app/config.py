from pepe_quote_core import MarketDataMode, validate_market_data_policy
from pydantic import Field
from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    environment: str = "development"
    market_data_mode: MarketDataMode = MarketDataMode.DEMO
    redis_url: str = "redis://localhost:6379/0"
    quote_cache_url: str = "redis://localhost:6379/1"
    quote_cache_namespace: str = "pepe:quotes:v1"
    quote_cache_ttl_seconds: int = Field(default=60, gt=0)
    quote_refresh_lease_ttl_seconds: int = Field(default=120, gt=0)
    database_url: str = "postgresql+asyncpg://pepe:change_me@localhost:5432/pepe"
    quote_queue_name: str = "quotes"
    candle_queue_name: str = "candles"
    candle_sync_lease_ttl_seconds: int = Field(default=300, gt=0)
    candle_scheduler_interval_seconds: int = Field(default=300, gt=0)
    candle_fake_provider_enabled: bool = False
    quote_fake_provider_enabled: bool = False
    quote_scheduler_interval_seconds: int = Field(default=60, gt=0)
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}

    def model_post_init(self, __context: object) -> None:
        validate_market_data_policy(
            environment=self.environment,
            mode=self.market_data_mode,
            quote_fake_provider_enabled=self.quote_fake_provider_enabled,
            candle_fake_provider_enabled=self.candle_fake_provider_enabled,
        )


worker_settings = WorkerSettings()
