"""Centralised settings loaded from environment variables / .env file.

A single import-time `get_settings()` call keeps the rest of the code clean
and gives us a single chokepoint to validate configuration on startup.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve a `.env` file living at the backend folder root regardless of where
# the process is launched from. This matters because Railway runs the app from
# `/app` while local dev runs it from `backend/`.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """All runtime configuration for the API."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Allow extra keys in `.env` so we don't bomb when bot-only vars
        # (WEBAPP_URL, etc.) are mixed into a shared environment.
        extra="ignore",
    )

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")

    database_url: str = Field(default="sqlite:///./dev.db", alias="DATABASE_URL")

    allowed_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="ALLOWED_ORIGINS",
    )

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    require_telegram_auth: bool = Field(
        default=False, alias="REQUIRE_TELEGRAM_AUTH"
    )

    # Admin dashboard (/api/admin/*). JWT is signed with this secret — use a long
    # random value in production. Login password is ADMIN_DASHBOARD_PASSWORD.
    admin_jwt_secret: str = Field(default="", alias="ADMIN_JWT_SECRET")
    admin_dashboard_password: str = Field(default="", alias="ADMIN_DASHBOARD_PASSWORD")
    admin_jwt_expire_hours: int = Field(default=8, alias="ADMIN_JWT_EXPIRE_HOURS", ge=1, le=720)

    anticheat_min_run_ms: int = Field(
        default=2000, alias="ANTICHEAT_MIN_RUN_MS"
    )

    anticheat_max_score_per_second: int = Field(
        default=80, alias="ANTICHEAT_MAX_SCORE_PER_SECOND"
    )

    @property
    def origins_list(self) -> list[str]:
        """Comma-separated env value parsed into a clean list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def database_url_normalized(self) -> str:
        """Railway and Heroku still ship DATABASE_URL as ``postgres://`` for
        legacy reasons; SQLAlchemy 2 wants ``postgresql+psycopg2://``. This
        property quietly fixes the URL so we don't have to babysit deploys.
        """
        url = self.database_url
        if url.startswith("postgres://"):
            return "postgresql+psycopg2://" + url[len("postgres://") :]
        if url.startswith("postgresql://") and "+psycopg" not in url:
            return "postgresql+psycopg2://" + url[len("postgresql://") :]
        return url

    @property
    def admin_enabled(self) -> bool:
        return bool(self.admin_dashboard_password.strip() and self.admin_jwt_secret.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
