from pydantic_settings import BaseSettings


class BotSettings(BaseSettings):
    telegram_bot_token: str = ""
    mini_app_url: str = "http://localhost"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}


bot_settings = BotSettings()
