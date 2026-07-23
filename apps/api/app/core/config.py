from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Pepe"
    app_slug: str = "pepe"
    version: str = "0.1.0"
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"),
    )

    database_url: str = "postgresql+asyncpg://pepe:change_me@localhost:5432/pepe"
    redis_url: str = "redis://localhost:6379/0"
    telegram_bot_token: str = ""
    mini_app_url: str = "http://localhost"
    telegram_init_data_max_age_seconds: int = 3600
    telegram_init_data_future_skew_seconds: int = 30
    cors_allowed_origins: str = "http://localhost,http://127.0.0.1"
    session_cookie_name: str = "pepe_session"
    session_absolute_ttl_seconds: int = 2_592_000
    session_idle_ttl_seconds: int = 604_800
    session_max_active: int = 5
    session_cookie_secure: bool = False
    session_allowed_origins: str = (
        "http://localhost:3000,http://localhost:4000,http://localhost:8080"
    )
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = {"env_file": ".env", "extra": "ignore", "populate_by_name": True}

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def session_origins(self) -> tuple[str, ...]:
        return tuple(
            origin.strip() for origin in self.session_allowed_origins.split(",") if origin.strip()
        )

    @model_validator(mode="after")
    def validate_session_settings(self) -> "Settings":
        normalized_environment = self.environment.strip().lower()
        self.environment = normalized_environment
        if not self.session_cookie_name:
            raise ValueError("session_cookie_name must not be empty")
        if self.session_absolute_ttl_seconds != 2_592_000:
            raise ValueError("session_absolute_ttl_seconds must equal 2592000")
        if self.session_idle_ttl_seconds != 604_800:
            raise ValueError("session_idle_ttl_seconds must equal 604800")
        if self.session_max_active != 5:
            raise ValueError("session_max_active must equal 5 for the approved contract")
        if self.environment == "production" and not self.session_cookie_secure:
            raise ValueError("session_cookie_secure must be true in production")
        if self.environment == "production" and not self.session_origins:
            raise ValueError("session_allowed_origins must not be empty in production")

        for origin in self.session_origins:
            try:
                parsed = urlsplit(origin)
                _port = parsed.port
            except ValueError as error:
                raise ValueError(
                    "session_allowed_origins must contain absolute HTTP/HTTPS origins",
                ) from error
            if (
                origin == "null"
                or "*" in origin
                or parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise ValueError("session_allowed_origins must contain absolute HTTP/HTTPS origins")
        return self


settings = Settings()
