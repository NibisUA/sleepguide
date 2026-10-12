from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.db_url import normalize_database_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "postgresql+asyncpg://sleepguide:sleepguide@localhost:5432/sleepguide"

    bot_token: str = ""
    mini_app_url: str = ""
    webhook_base_url: str = ""
    webhook_secret: str = ""

    jwt_secret: str = "change-me"
    jwt_ttl_minutes: int = 60
    init_data_max_age_seconds: int = 86400

    cors_origins: list[str] = ["http://localhost:5173"]
    dev_login_enabled: bool = False
    reminders_enabled: bool = True  # background reminder loop (needs BOT_TOKEN)
    trusted_proxy_ips: list[str] = ["127.0.0.1", "::1"]

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return normalize_database_url(value)

    def validate_for_runtime(self) -> None:
        if self.env == "prod":
            if len(self.jwt_secret.encode()) < 32:
                raise RuntimeError("JWT_SECRET must contain at least 32 bytes in production")
            if not self.bot_token:
                raise RuntimeError("BOT_TOKEN must be set in production")
            if self.dev_login_enabled:
                raise RuntimeError("DEV_LOGIN_ENABLED must be false in production")
            if len(self.webhook_secret) < 32:
                raise RuntimeError("WEBHOOK_SECRET must contain at least 32 characters")
            for url in (self.mini_app_url, self.webhook_base_url):
                if not url.startswith("https://"):
                    raise RuntimeError("Production Mini App and webhook URLs must use HTTPS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
