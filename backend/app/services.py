"""Small data-layer helpers shared across route modules.

Anything that touches more than one ORM model (e.g. upsert + aggregate
recompute) belongs here so the routes stay declarative.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .auth import TelegramUser
from .models import User


def upsert_user(db: Session, tg_user: TelegramUser) -> User:
    """Look up the user by Telegram id; create on first sight, refresh
    profile fields (display name, photo, etc.) on every visit so the
    leaderboard doesn't show stale names.
    """
    user = db.get(User, tg_user.id)
    now = datetime.now(timezone.utc)

    if user is None:
        user = User(
            id=tg_user.id,
            name=tg_user.display_name,
            username=tg_user.username,
            photo_url=tg_user.photo_url,
            language=tg_user.language_code,
            best_score=0,
            total_coins=0,
            runs_played=0,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        db.flush()
        return user

    # Always refresh mutable profile fields. Cheap, and means the leaderboard
    # immediately reflects a name change.
    user.name = tg_user.display_name
    user.username = tg_user.username
    user.photo_url = tg_user.photo_url
    user.language = tg_user.language_code
    user.updated_at = now
    return user
