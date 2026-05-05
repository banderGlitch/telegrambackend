"""Application configuration loaded from environment variables."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a .env file located next to this module, if present.
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    bot_token: str
    log_level: int
    webapp_url: str | None

    @classmethod
    def load(cls) -> "Settings":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token or token == "your-bot-token-here":
            raise ConfigError(
                "TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env "
                "and paste the token you got from @BotFather."
            )

        level_name = os.getenv("LOG_LEVEL", "INFO").upper().strip()
        log_level = getattr(logging, level_name, logging.INFO)

        # WEBAPP_URL is optional. Telegram requires https for web_app buttons,
        # so we only treat it as configured when it actually starts with https://.
        raw_webapp = os.getenv("WEBAPP_URL", "").strip()
        webapp_url = raw_webapp if raw_webapp.startswith("https://") else None

        return cls(bot_token=token, log_level=log_level, webapp_url=webapp_url)


settings: Settings | None = None


def get_settings() -> Settings:
    """Return a cached Settings instance, loading it on first access."""
    global settings
    if settings is None:
        settings = Settings.load()
    return settings
