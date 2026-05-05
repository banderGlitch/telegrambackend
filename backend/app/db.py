"""SQLAlchemy engine + session factory.

We use the synchronous engine because the request volume for this MVP is
trivially low and synchronous code paths are dramatically easier to debug.
Switching to async later is mechanical: `create_async_engine` + `AsyncSession`.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    """Single metadata namespace shared by every ORM model."""


def _build_engine() -> Engine:
    settings = get_settings()
    url = settings.database_url_normalized
    # SQLite needs `check_same_thread=False` because FastAPI's threadpool
    # passes connections across threads. Postgres ignores connect_args.
    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
        future=True,
    )


engine: Engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a session and guarantees close."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
