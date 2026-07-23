from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Pepe"
    app_slug: str = "pepe"
    version: str = "0.1.0"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://pepe:change_me@localhost:5432/pepe"
    redis_url: str = "redis://localhost:6379/0"

    telegram_bot_token: str = ""
    mini_app_url: str = "http://localhost"

    telegram_init_data_max_age_seconds: int = 3600
    telegram_init_data_future_skew_seconds: int = 30

    cors_allowed_origins: str = "http://localhost,http://127.0.0.1"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


settings = Settings()
