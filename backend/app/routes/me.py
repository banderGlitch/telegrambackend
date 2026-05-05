"""GET /api/me — the authenticated player's profile + recent run history."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import TelegramUser, require_user
from ..db import get_db
from ..models import Run, User
from ..schemas import MeResponse, MeStats, MeUser, RunPublic
from ..services import upsert_user


router = APIRouter()

# How many recent runs to return on /me. Mirrors the frontend's
# `HISTORY_LIMIT` so the UI never has to ask for more than this.
RECENT_RUNS = 50


@router.get("/me", response_model=MeResponse, response_model_by_alias=True)
def get_me(
    db: Session = Depends(get_db),
    tg_user: TelegramUser = Depends(require_user),
) -> MeResponse:
    user = upsert_user(db, tg_user)

    recent_runs = (
        db.execute(
            select(Run)
            .where(Run.user_id == user.id, Run.ended_at.is_not(None))
            .order_by(Run.ended_at.desc())
            .limit(RECENT_RUNS)
        )
        .scalars()
        .all()
    )

    return MeResponse(
        user=MeUser(
            id=user.id,
            name=user.name,
            username=user.username,
            photo_url=user.photo_url,
            language=user.language,
        ),
        stats=MeStats(
            best_score=user.best_score,
            total_coins=user.total_coins,
            runs_played=user.runs_played,
        ),
        recent=[RunPublic.model_validate(r) for r in recent_runs],
    )
