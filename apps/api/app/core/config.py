from typing import Literal
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    _synthetic_quote_source_label = "Synthetic test source"
    _synthetic_quote_venue_label = "Synthetic test venue"

    app_name: str = "Pepe"
    app_slug: str = "pepe"
    version: str = "0.1.0"
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"),
    )

    database_url: str = "postgresql+asyncpg://pepe:change_me@localhost:5432/pepe"
    redis_url: str = "redis://localhost:6379/0"
    quote_cache_url: str = "redis://localhost:6379/1"
    quote_cache_namespace: str = "pepe:quotes:v1"
    quote_cache_ttl_seconds: int = 60
    quote_fake_provider_enabled: bool = False
    quote_source_label: str = _synthetic_quote_source_label
    quote_venue_label: str = _synthetic_quote_venue_label
    quote_crypto_stale_after_seconds: int = 60
    quote_crypto_hard_expire_after_seconds: int = 300
    quote_reference_stale_after_seconds: int = 300
    quote_reference_hard_expire_after_seconds: int = 900
    quote_api_batch_limit: int = 20
    telegram_bot_token: str = ""
    mini_app_url: str = "http://localhost"
    telegram_init_data_max_age_seconds: int = 3600
    telegram_init_data_future_skew_seconds: int = 30
    cors_allowed_origins: str = "http://localhost:3000,http://localhost:4000,http://localhost:8080"
    session_cookie_name: str = "pepe_session"
    session_absolute_ttl_seconds: int = 2_592_000
    session_idle_ttl_seconds: int = 604_800
    session_max_active: int = 5
    session_cookie_secure: bool = False
    session_cookie_same_site: Literal["lax", "strict", "none"] = "lax"
    session_cookie_partitioned: bool = False
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
        if self.session_cookie_same_site == "none" and not self.session_cookie_secure:
            raise ValueError(
                "session_cookie_secure must be true when session_cookie_same_site is none",
            )
        if self.session_cookie_partitioned and self.session_cookie_same_site != "none":
            raise ValueError(
                "session_cookie_same_site must be none when session_cookie_partitioned is true",
            )
        if self.environment == "production" and not self.session_origins:
            raise ValueError("session_allowed_origins must not be empty in production")
        if self.environment == "production" and self.quote_fake_provider_enabled:
            raise ValueError("quote_fake_provider_enabled must be false in production")
        if self.environment == "production" and (
            not self.quote_source_label.strip()
            or self.quote_source_label == self._synthetic_quote_source_label
            or self.quote_venue_label == self._synthetic_quote_venue_label
        ):
            raise ValueError("production quote labels must not use synthetic placeholders")
        if self.quote_crypto_stale_after_seconds <= 0 or (
            self.quote_crypto_hard_expire_after_seconds <= self.quote_crypto_stale_after_seconds
        ):
            raise ValueError("crypto quote freshness thresholds are invalid")
        if self.quote_reference_stale_after_seconds <= 0 or (
            self.quote_reference_hard_expire_after_seconds
            <= self.quote_reference_stale_after_seconds
        ):
            raise ValueError("reference quote freshness thresholds are invalid")
        if not 1 <= self.quote_api_batch_limit <= 100:
            raise ValueError("quote_api_batch_limit must be between 1 and 100")
        if self.quote_cache_ttl_seconds <= 0:
            raise ValueError("quote_cache_ttl_seconds must be positive")

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
        if not set(self.session_origins).issubset(self.cors_origins):
            raise ValueError("session_allowed_origins must be included in cors_allowed_origins")
        return self

    def quote_freshness_for(self, asset_class: str) -> tuple[int, int]:
        if asset_class == "crypto_spot":
            return (
                self.quote_crypto_stale_after_seconds,
                self.quote_crypto_hard_expire_after_seconds,
            )
        return (
            self.quote_reference_stale_after_seconds,
            self.quote_reference_hard_expire_after_seconds,
        )


settings = Settings()
