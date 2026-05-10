"""FastAPI application entrypoint.

Run locally:
    uvicorn app.main:app --reload --port 8000

Run in production (Railway):
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import Base, engine
from .routes.admin import router as admin_router
from .routes.leaderboard import router as leaderboard_router
from .routes.me import router as me_router
from .routes.runs import router as runs_router


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
    )


def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging(settings.log_level)
    log = logging.getLogger(__name__)

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        yield
        from .redis_client import close_redis

        close_redis()

    # Register ORM tables on ``Base.metadata`` before ``create_all``.
    from . import models as _models  # noqa: F401

    # Auto-create tables on first boot if no migrations have been run.
    # In production we run Alembic instead and this is a no-op (Base sees
    # tables already exist). For SQLite local dev this gives a zero-config
    # startup experience.
    Base.metadata.create_all(bind=engine)
    log.info("Database ready: %s", _redact_url(settings.database_url_normalized))

    app = FastAPI(
        title="Asteroid Dodger API",
        version="0.1.0",
        description=(
            "Backend for the Asteroid Dodger Telegram Mini App. "
            "Authenticates Telegram WebApp initData via HMAC, persists run "
            "history, and serves the global leaderboard."
        ),
        lifespan=_lifespan,
    )

    # Regex covers dev servers on common loopback forms ( [::1] is still a
    # different browser Origin than localhost / 127.0.0.1 ).
    _local_origin_regex = r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\\d+)?$"
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_origin_regex=_local_origin_regex,
        allow_credentials=False,  # we don't use cookies
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "X-Telegram-Init-Data",
            "Authorization",
        ],
        max_age=600,
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(me_router, prefix="/api", tags=["me"])
    app.include_router(runs_router, prefix="/api", tags=["runs"])
    app.include_router(leaderboard_router, prefix="/api", tags=["leaderboard"])
    app.include_router(admin_router, prefix="/api")

    log.info(
        "App configured. require_telegram_auth=%s allowed_origins=%s",
        settings.require_telegram_auth,
        settings.origins_list,
    )
    return app


def _redact_url(url: str) -> str:
    """Hide the password in a database URL before logging it."""
    if "@" not in url or "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" not in rest:
        return url
    creds, host = rest.rsplit("@", 1)
    if ":" in creds:
        user, _ = creds.split(":", 1)
        creds = f"{user}:***"
    return f"{scheme}://{creds}@{host}"


app = create_app()
