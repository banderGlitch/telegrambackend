"""POST /api/runs/start  +  POST /api/runs/end

Lifecycle of a run row:
  start → row inserted with score=0, ended_at=NULL, server-issued id
  end   → row finalised; user aggregates updated; leaderboard rank computed
"""

from __future__ import annotations

import logging
import secrets
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..anticheat import evaluate_run
from ..auth import TelegramUser, require_user
from ..config import Settings, get_settings
from ..db import get_db
from ..models import Run, User
from ..schemas import (
    MeStats,
    RunEndRequest,
    RunEndResponse,
    RunStartResponse,
)
from ..services import upsert_user


router = APIRouter()
log = logging.getLogger(__name__)


def _generate_run_id() -> str:
    """Server-side run identifier. URL-safe, 22 chars of entropy.

    Using server-issued ids means the client can't forge a run id that
    "doesn't exist" in our database, which makes /runs/end's existence
    check meaningful.
    """
    return f"r_{secrets.token_urlsafe(16)}"


@router.post(
    "/runs/start",
    response_model=RunStartResponse,
    response_model_by_alias=True,
)
def start_run(
    db: Session = Depends(get_db),
    tg_user: TelegramUser = Depends(require_user),
) -> RunStartResponse:
    user = upsert_user(db, tg_user)
    now = datetime.now(timezone.utc)

    run = Run(
        id=_generate_run_id(),
        user_id=user.id,
        score=0,
        coins=0,
        duration_ms=0,
        near_misses=0,
        started_at=now,
        ended_at=None,
    )
    db.add(run)
    db.commit()

    return RunStartResponse(
        run_id=run.id,
        server_time_ms=int(now.timestamp() * 1000),
    )


@router.post(
    "/runs/end",
    response_model=RunEndResponse,
    response_model_by_alias=True,
)
def end_run(
    body: RunEndRequest,
    db: Session = Depends(get_db),
    tg_user: TelegramUser = Depends(require_user),
    settings: Settings = Depends(get_settings),
) -> RunEndResponse:
    run = db.get(Run, body.run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="run_id not found — did you call /runs/start?",
        )
    if run.user_id != tg_user.id:
        # Someone trying to finalise a run they didn't start.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="run does not belong to this user",
        )

    user = db.get(User, tg_user.id)
    assert user is not None  # upsert at /runs/start guarantees this

    # Idempotency: if the row already has `ended_at` set, return the existing
    # state instead of double-counting. This is a nice safety net for flaky
    # mobile networks where /runs/end might be retried after a 200 was sent.
    if run.ended_at is not None:
        rank = _compute_rank(db, user.id)
        return RunEndResponse(
            accepted=True,
            new_best=user.best_score == run.score and run.score > 0,
            rank=rank,
            stats=MeStats(
                best_score=user.best_score,
                total_coins=user.total_coins,
                runs_played=user.runs_played,
            ),
        )

    now = datetime.now(timezone.utc)
    verdict = evaluate_run(
        score=body.score,
        coins=body.coins,
        duration_ms=body.duration_ms,
        started_at=run.started_at,
        now=now,
        min_run_ms=settings.anticheat_min_run_ms,
        max_score_per_second=settings.anticheat_max_score_per_second,
    )

    if not verdict.accepted:
        log.warning(
            "anti-cheat rejected run %s for user %s: %s",
            run.id,
            user.id,
            verdict.reason,
        )
        # Drop the row entirely so the player's history stays clean. The same
        # run id can never be reused (each /runs/start mints a fresh one), so
        # there's no idempotency concern. If we later want to track rejection
        # rates for monitoring, add a separate `rejection_log` table.
        db.delete(run)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"run rejected: {verdict.reason}",
        )

    # Happy path. Finalise the run row + bump aggregates.
    run.score = body.score
    run.coins = body.coins
    run.duration_ms = body.duration_ms
    run.near_misses = body.near_misses
    run.ended_at = now

    new_best = body.score > user.best_score
    if new_best:
        user.best_score = body.score
    user.total_coins += body.coins
    user.runs_played += 1
    user.updated_at = now

    db.commit()
    db.refresh(user)

    return RunEndResponse(
        accepted=True,
        new_best=new_best,
        rank=_compute_rank(db, user.id),
        stats=MeStats(
            best_score=user.best_score,
            total_coins=user.total_coins,
            runs_played=user.runs_played,
        ),
    )


def _compute_rank(db: Session, user_id: int) -> int | None:
    """Return the user's 1-indexed position on the all-time best leaderboard.

    None if the user has no recorded best yet.
    """
    user = db.get(User, user_id)
    if user is None or user.best_score <= 0:
        return None

    # Count how many other users have a strictly higher best_score; rank is
    # that count + 1. Tie-breaking is "first to achieve" implicitly since we
    # use strict greater-than.
    higher = db.scalar(
        select(func.count(User.id)).where(User.best_score > user.best_score)
    )
    return int(higher or 0) + 1
