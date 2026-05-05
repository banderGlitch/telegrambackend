"""GET /api/leaderboard — top scores ever (one entry per user, by best_score).

We rank by `User.best_score` rather than scanning Run rows. That makes the
query trivial (single sorted index lookup) and keeps the leaderboard stable
even when a player has many runs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..auth import TelegramUser, require_user
from ..db import get_db
from ..models import User
from ..schemas import LeaderboardEntry, LeaderboardResponse


router = APIRouter()


@router.get(
    "/leaderboard",
    response_model=LeaderboardResponse,
    response_model_by_alias=True,
)
def get_leaderboard(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    tg_user: TelegramUser = Depends(require_user),
) -> LeaderboardResponse:
    rows = (
        db.execute(
            select(User)
            .where(User.best_score > 0)
            .order_by(desc(User.best_score), User.id.asc())
            .limit(limit)
        )
        .scalars()
        .all()
    )

    entries = [
        LeaderboardEntry(
            rank=i + 1,
            user_id=u.id,
            name=u.name,
            score=u.best_score,
            is_self=(u.id == tg_user.id),
        )
        for i, u in enumerate(rows)
    ]

    self_rank: int | None = None
    for entry in entries:
        if entry.is_self:
            self_rank = entry.rank
            break

    # If the player isn't in the top-N, compute their global rank explicitly
    # so the UI can still show "#412".
    if self_rank is None and tg_user.id != 0:
        from sqlalchemy import func

        self_user = db.get(User, tg_user.id)
        if self_user is not None and self_user.best_score > 0:
            higher = db.scalar(
                select(func.count(User.id)).where(
                    User.best_score > self_user.best_score
                )
            )
            self_rank = int(higher or 0) + 1

    return LeaderboardResponse(entries=entries, self_rank=self_rank)
