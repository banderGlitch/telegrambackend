"""Browser admin dashboard API — JWT login + read-only player intelligence + Telegram sends."""

from __future__ import annotations

import csv
import json
import logging
import secrets
from collections import Counter
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, and_, exists, func, or_, select
from sqlalchemy.orm import Session

from ..admin_auth import issue_admin_token, require_admin_token
from ..config import Settings, get_settings
from ..db import get_db
from ..models import AdminMessageLog, Run, User
from ..schemas import (
    AdminInsightResponse,
    AdminLiveSessionRow,
    AdminLiveSessionsResponse,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminMessageLogListResponse,
    AdminMessageLogPublic,
    AdminOutboundRequest,
    AdminOutboundResult,
    AdminOverviewResponse,
    AdminUserDetailResponse,
    AdminUsersPage,
    RunAdminPublic,
    UserAdminPublic,
)
from ..telegram_outbound import send_telegram_message

router = APIRouter(prefix="/admin", tags=["admin"])
log = logging.getLogger(__name__)


def _ensure_admin_config(settings: Settings) -> None:
    if not settings.admin_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API is disabled (set ADMIN_DASHBOARD_PASSWORD and ADMIN_JWT_SECRET)",
        )


@router.post("/auth/login", response_model=AdminLoginResponse, response_model_by_alias=True)
def admin_login(
    body: AdminLoginRequest,
    settings: Settings = Depends(get_settings),
) -> AdminLoginResponse:
    _ensure_admin_config(settings)
    if not secrets.compare_digest(body.password, settings.admin_dashboard_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    token, hours = issue_admin_token(settings)
    return AdminLoginResponse(access_token=token, expires_in_hours=hours)


@router.get("/overview", response_model=AdminOverviewResponse, response_model_by_alias=True, dependencies=[Depends(require_admin_token)])
def admin_overview(
    db: Session = Depends(get_db),
) -> AdminOverviewResponse:
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    inactive_cutoff = now - timedelta(days=14)

    total_users = int(db.scalar(select(func.count()).select_from(User)) or 0)

    total_completed = int(
        db.scalar(select(func.count()).select_from(Run).where(Run.ended_at.isnot(None))) or 0
    )
    total_open = int(
        db.scalar(select(func.count()).select_from(Run).where(Run.ended_at.is_(None))) or 0
    )
    runs_last_24h = int(
        db.scalar(
            select(func.count())
            .select_from(Run)
            .where(Run.ended_at.isnot(None), Run.ended_at >= day_ago)
        )
        or 0
    )
    new_users_7d = int(
        db.scalar(select(func.count()).select_from(User).where(User.created_at >= week_ago)) or 0
    )

    # Users who have not finished a run in the last 14 days (UTC).
    inactive_cutoff = now - timedelta(days=14)
    no_recent_complete = ~exists(
        select(1).where(
            Run.user_id == User.id,
            Run.ended_at.isnot(None),
            Run.ended_at >= inactive_cutoff,
        )
    )
    dormant_users_14d = int(
        db.scalar(select(func.count()).select_from(User).where(User.id > 0, no_recent_complete)) or 0
    )

    # Completed runs per calendar day (UTC), last 7 days — aggregate in Python
    # because ``cast(timestamp, DATE) GROUP BY`` trips SQLite+Cython date parsers.
    day_keys: list[str] = []
    for i in range(6, -1, -1):
        d = (now - timedelta(days=i)).date()
        day_keys.append(d.isoformat())

    ends = db.scalars(
        select(Run.ended_at).where(
            Run.ended_at.isnot(None),
            Run.ended_at >= now - timedelta(days=7),
        )
    ).all()
    raw_counts: Counter[str] = Counter()
    for ended_at in ends:
        dt = ended_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        raw_counts[dt.date().isoformat()] += 1

    runs_by_day = [{"date": k, "count": raw_counts[k]} for k in day_keys]

    return AdminOverviewResponse(
        total_users=total_users,
        total_completed_runs=total_completed,
        open_runs=total_open,
        runs_last_24h=runs_last_24h,
        new_users_7d=new_users_7d,
        dormant_users_14d=dormant_users_14d,
        runs_by_day=runs_by_day,
    )


def _dt_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def live_sessions_data(
    db: Session,
    *,
    threshold_minutes: int = 45,
    limit: int = 80,
) -> AdminLiveSessionsResponse:
    """Core query for open runs — callable from tests without FastAPI ``Query`` wrappers."""
    now = datetime.now(timezone.utc)
    thresh = timedelta(minutes=threshold_minutes)

    stmt = (
        select(Run, User)
        .join(User, Run.user_id == User.id)
        .where(Run.ended_at.is_(None))
        .order_by(Run.started_at.desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    items: list[AdminLiveSessionRow] = []
    for run, user in rows:
        st = _dt_utc(run.started_at)
        age = now - st
        items.append(
            AdminLiveSessionRow(
                user_id=int(user.id),
                name=user.name,
                username=user.username,
                run_id=run.id,
                started_at=st,
                presumed_in_game=age <= thresh,
            )
        )

    return AdminLiveSessionsResponse(
        threshold_minutes=threshold_minutes,
        total_returned=len(items),
        items=items,
    )


@router.get(
    "/sessions/live",
    response_model=AdminLiveSessionsResponse,
    response_model_by_alias=True,
    dependencies=[Depends(require_admin_token)],
)
def admin_live_sessions(
    db: Session = Depends(get_db),
    threshold_minutes: Annotated[
        int,
        Query(
            ge=5,
            le=1440,
            description="Runs started within this many minutes are flagged as likely still playing.",
        ),
    ] = 45,
    limit: Annotated[int, Query(ge=1, le=300)] = 80,
) -> AdminLiveSessionsResponse:
    """Open runs (``ended_at`` NULL) joined to user — best available “who might be in a match”."""
    return live_sessions_data(db, threshold_minutes=threshold_minutes, limit=limit)


@router.get(
    "/insights/dormant",
    response_model=AdminInsightResponse,
    response_model_by_alias=True,
    dependencies=[Depends(require_admin_token)],
)
def admin_insight_dormant(
    db: Session = Depends(get_db),
    days: int = Query(14, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
) -> AdminInsightResponse:
    """Players with no *completed* run in the last `days` — good re-engagement list."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    no_recent = ~exists(
        select(1).where(
            Run.user_id == User.id,
            Run.ended_at.isnot(None),
            Run.ended_at >= cutoff,
        )
    )
    rows = db.execute(
        select(User.id, User.name, User.username, User.best_score, User.updated_at)
        .where(User.id > 0, no_recent)
        .order_by(User.best_score.desc())
        .limit(limit)
    ).all()
    sample = [
        {
            "id": int(r[0]),
            "name": r[1],
            "username": r[2],
            "best_score": int(r[3]),
            "updated_at": r[4].astimezone(timezone.utc).isoformat() if r[4] else None,
        }
        for r in rows
    ]
    return AdminInsightResponse(
        title=f"No completed run in {days} days (top {limit} by best score)",
        count=len(sample),
        sample=sample,
    )


@router.get("/users", response_model=AdminUsersPage, response_model_by_alias=True, dependencies=[Depends(require_admin_token)])
def admin_list_users(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, max_length=80),
    sort: str = Query("updated", pattern="^(updated|created|best_score|runs_played)$"),
) -> AdminUsersPage:
    filters = []
    if search and search.strip():
        s = f"%{search.strip()}%"
        conds = [User.name.ilike(s), User.username.ilike(s)]
        if search.strip().isdigit():
            conds.append(User.id == int(search.strip()))
        filters.append(or_(*conds))

    filt = and_(*filters) if filters else None

    count_stmt = select(func.count()).select_from(User)
    stmt: Select[User] = select(User)
    if filt is not None:
        count_stmt = count_stmt.where(filt)
        stmt = stmt.where(filt)

    total = int(db.scalar(count_stmt) or 0)

    order_map = {
        "updated": User.updated_at.desc(),
        "created": User.created_at.desc(),
        "best_score": User.best_score.desc(),
        "runs_played": User.runs_played.desc(),
    }
    stmt = stmt.order_by(order_map[sort])
    offset = (page - 1) * page_size
    rows = db.execute(stmt.offset(offset).limit(page_size)).scalars().all()

    return AdminUsersPage(
        total=total,
        page=page,
        page_size=page_size,
        items=[UserAdminPublic.model_validate(u) for u in rows],
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse, response_model_by_alias=True, dependencies=[Depends(require_admin_token)])
def admin_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    runs_limit: int = Query(80, ge=1, le=200),
) -> AdminUserDetailResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="user not found")

    runs_stmt: Select[tuple[Run]] = (
        select(Run)
        .where(Run.user_id == user_id)
        .order_by(Run.started_at.desc())
        .limit(runs_limit)
    )
    runs = db.execute(runs_stmt).scalars().all()

    opened = sum(1 for r in runs if r.ended_at is None)
    completed = sum(1 for r in runs if r.ended_at is not None)

    return AdminUserDetailResponse(
        user=UserAdminPublic.model_validate(user),
        runs=[RunAdminPublic.model_validate(r) for r in runs],
        runs_open_in_sample=opened,
        runs_completed_in_sample=completed,
    )


def _persist_message_log(
    db: Session,
    *,
    scope: str,
    recipient_count: int,
    success: int,
    fail: int,
    recipient_user_id: int | None,
    text_preview: str,
    errors: list[str],
) -> AdminMessageLog:
    err_payload = json.dumps(errors[:40]) if errors else None
    row = AdminMessageLog(
        scope=scope,
        recipient_count=recipient_count,
        success_count=success,
        fail_count=fail,
        recipient_user_id=recipient_user_id,
        text_preview=text_preview[:256],
        errors_json=err_payload[:4096] if err_payload else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post(
    "/messages/send",
    response_model=AdminOutboundResult,
    response_model_by_alias=True,
    dependencies=[Depends(require_admin_token)],
)
def admin_send_one(
    body: AdminOutboundRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminOutboundResult:
    if body.user_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="userId is required for direct send")
    if not settings.telegram_bot_token.strip():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="TELEGRAM_BOT_TOKEN missing")
    u = db.get(User, body.user_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="user not found")

    ok, err = send_telegram_message(
        settings.telegram_bot_token,
        int(body.user_id),
        body.text,
        parse_mode=body.parse_mode,
    )
    errors = [] if ok else [err]
    _persist_message_log(
        db,
        scope="single",
        recipient_count=1,
        success=1 if ok else 0,
        fail=0 if ok else 1,
        recipient_user_id=int(body.user_id),
        text_preview=body.text,
        errors=errors,
    )
    return AdminOutboundResult(sent=1 if ok else 0, failed=0 if ok else 1, errors=errors)


@router.post(
    "/messages/broadcast",
    response_model=AdminOutboundResult,
    response_model_by_alias=True,
    dependencies=[Depends(require_admin_token)],
)
def admin_broadcast(
    body: AdminOutboundRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminOutboundResult:
    """Send the same text to every stored player (excludes synthetic id 0)."""
    if not settings.telegram_bot_token.strip():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="TELEGRAM_BOT_TOKEN missing")
    if body.user_id is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="user_id must be omitted for broadcast")

    ids = db.execute(select(User.id).where(User.id > 0).order_by(User.id)).scalars().all()
    if len(ids) > 5000:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Too many recipients; contact support to raise the cap safely.",
        )

    sent = 0
    failed = 0
    errors: list[str] = []
    for uid in ids:
        ok, err = send_telegram_message(
            settings.telegram_bot_token,
            int(uid),
            body.text,
            parse_mode=body.parse_mode,
        )
        if ok:
            sent += 1
        else:
            failed += 1
            if len(errors) < 25:
                errors.append(f"{uid}: {err}")

    _persist_message_log(
        db,
        scope="broadcast",
        recipient_count=len(ids),
        success=sent,
        fail=failed,
        recipient_user_id=None,
        text_preview=body.text,
        errors=errors,
    )
    log.info(
        "admin broadcast finished: recipients=%s sent=%s failed=%s",
        len(ids),
        sent,
        failed,
    )
    return AdminOutboundResult(sent=sent, failed=failed, errors=errors)


@router.get(
    "/messages/log",
    response_model=AdminMessageLogListResponse,
    response_model_by_alias=True,
    dependencies=[Depends(require_admin_token)],
)
def admin_message_log(
    db: Session = Depends(get_db),
    limit: int = Query(40, ge=1, le=200),
) -> AdminMessageLogListResponse:
    rows = (
        db.execute(select(AdminMessageLog).order_by(AdminMessageLog.id.desc()).limit(limit))
        .scalars()
        .all()
    )
    return AdminMessageLogListResponse(
        items=[AdminMessageLogPublic.model_validate(r) for r in rows],
    )


@router.get("/export/users.csv", dependencies=[Depends(require_admin_token)])
def admin_export_users_csv(db: Session = Depends(get_db)) -> StreamingResponse:
    """Download full player roster as CSV (for CRM / external tools)."""
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "telegram_id",
            "name",
            "username",
            "language",
            "best_score",
            "total_coins",
            "runs_played",
            "created_at",
            "updated_at",
        ]
    )
    for u in db.execute(select(User).order_by(User.id)).scalars():
        w.writerow(
            [
                u.id,
                u.name,
                u.username or "",
                u.language or "",
                u.best_score,
                u.total_coins,
                u.runs_played,
                u.created_at.astimezone(timezone.utc).isoformat(),
                u.updated_at.astimezone(timezone.utc).isoformat(),
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="asteroid_players.csv"'},
    )
