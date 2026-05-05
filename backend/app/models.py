"""ORM models.

Two tables — `users` for the per-Telegram-user record and `runs` for every
completed game session. We keep `runs` immutable: a row is inserted once on
`/runs/end` and never mutated; aggregates (`best_score`, `total_coins`,
`runs_played`) are recomputed on the user record at the same time so reads
are O(1).
"""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _utcnow() -> datetime:
    """Tz-aware default for created_at columns."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    # The Telegram user id is the primary key. It's a 64-bit integer so we use
    # BigInteger explicitly; SQLite collapses it to INTEGER which is fine.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # Aggregates — refreshed on every successful /runs/end submission.
    best_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    runs_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    runs: Mapped[list["Run"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Run(Base):
    """One completed game session.

    Lifecycle:
      * `/runs/start` inserts a row with `score=0, coins=0, ended_at=NULL`
        and returns its `id` to the client.
      * `/runs/end` looks up the row by id, validates the submitted
        score/coins against `started_at` + anti-cheat thresholds, and
        finalises it. Once `ended_at` is non-NULL the row is immutable.
      * Sessions left open (player closed the app mid-run) sit in the table
        with `ended_at=NULL`. We can age them out with a periodic job later.
    """

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    near_misses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    # NULL while the run is in flight; non-NULL once submitted.
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="runs")


# Composite index that powers the leaderboard query (`order by score desc`)
# and the per-user history query (`order by ended_at desc where user_id=?`).
Index("ix_runs_user_ended", Run.user_id, Run.ended_at.desc())
Index("ix_runs_score_desc", Run.score.desc())
