"""Pydantic request and response models.

Keep these dumb — they describe the wire format, nothing more. ORM ↔ schema
conversion lives in the route handlers so it's obvious what's persisted vs.
what's exposed to the client.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, field_serializer


def _utc_iso(dt: datetime) -> str:
    """Emit a datetime as ISO 8601 with an explicit `Z` suffix.

    SQLite drops timezone info on read, so naive datetimes coming back from
    the ORM are re-stamped as UTC. Postgres preserves tz and this becomes a
    no-op there. Either way, the wire format is unambiguous for the JS
    client which would otherwise interpret naive ISO as local time.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


# ─────────────────────────────  /me  ─────────────────────────────


class MeUser(BaseModel):
    id: int
    name: str
    username: str | None
    photo_url: str | None
    language: str | None


class MeStats(BaseModel):
    best_score: int
    total_coins: int
    runs_played: int


class RunPublic(BaseModel):
    """Single run, formatted for the frontend's run history list."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    score: int
    coins: int
    duration_ms: int = Field(serialization_alias="durationMs")
    ended_at: datetime = Field(serialization_alias="endedAt")

    @field_serializer("ended_at")
    def _serialize_ended_at(self, value: datetime) -> str:
        return _utc_iso(value)


class MeResponse(BaseModel):
    user: MeUser
    stats: MeStats
    recent: list[RunPublic]


# ────────────────────────  /runs/start, /end  ────────────────────────


class RunStartResponse(BaseModel):
    run_id: str = Field(serialization_alias="runId")
    server_time_ms: int = Field(serialization_alias="serverTimeMs")


class RunEndRequest(BaseModel):
    run_id: str = Field(alias="runId")
    score: int = Field(ge=0)
    coins: int = Field(ge=0)
    near_misses: int = Field(default=0, ge=0, alias="nearMisses")
    # Client-reported duration. We trust it as a *hint* and cross-check
    # against the server-side `started_at` timestamp on the row.
    duration_ms: int = Field(ge=0, alias="durationMs")


class RunEndResponse(BaseModel):
    accepted: bool
    new_best: bool = Field(serialization_alias="newBest")
    rank: int | None = None
    stats: MeStats


# ─────────────────────────  /leaderboard  ─────────────────────────


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int = Field(serialization_alias="userId")
    name: str
    score: int
    is_self: bool = Field(serialization_alias="isSelf")


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]
    self_rank: int | None = Field(default=None, serialization_alias="selfRank")


# ─────────────────────────  Admin dashboard  ─────────────────────────


class AdminLoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class AdminLoginResponse(BaseModel):
    access_token: str = Field(serialization_alias="accessToken")
    token_type: str = Field(default="bearer", serialization_alias="tokenType")
    expires_in_hours: int = Field(serialization_alias="expiresInHours")

    model_config = ConfigDict(populate_by_name=True)


class RunsByDay(BaseModel):
    date: str
    count: int


class AdminOverviewResponse(BaseModel):
    total_users: int = Field(serialization_alias="totalUsers")
    total_completed_runs: int = Field(serialization_alias="totalCompletedRuns")
    open_runs: int = Field(serialization_alias="openRuns")
    runs_last_24h: int = Field(serialization_alias="runsLast24h")
    new_users_7d: int = Field(serialization_alias="newUsers7d")
    dormant_users_14d: int = Field(serialization_alias="dormantUsers14d")
    runs_by_day: list[RunsByDay] = Field(serialization_alias="runsByDay")


class AdminInsightResponse(BaseModel):
    title: str
    count: int
    sample: list[dict]


class UserAdminPublic(BaseModel):
    """User row suitable for operator tables."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    username: str | None
    photo_url: str | None = Field(serialization_alias="photoUrl")
    language: str | None
    best_score: int = Field(serialization_alias="bestScore")
    total_coins: int = Field(serialization_alias="totalCoins")
    runs_played: int = Field(serialization_alias="runsPlayed")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")

    @field_serializer("created_at", "updated_at")
    def _dt(self, value: datetime) -> str:
        return _utc_iso(value)


class AdminUsersPage(BaseModel):
    total: int
    page: int
    page_size: int = Field(serialization_alias="pageSize")
    items: list[UserAdminPublic]


class RunAdminPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    score: int
    coins: int
    duration_ms: int = Field(serialization_alias="durationMs")
    near_misses: int = Field(serialization_alias="nearMisses")
    started_at: datetime = Field(serialization_alias="startedAt")
    ended_at: datetime | None = Field(default=None, serialization_alias="endedAt")

    @field_serializer("started_at", "ended_at")
    def _dt(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return _utc_iso(value)


class AdminUserDetailResponse(BaseModel):
    user: UserAdminPublic
    runs: list[RunAdminPublic]
    runs_open_in_sample: int = Field(serialization_alias="runsOpenInSample")
    runs_completed_in_sample: int = Field(serialization_alias="runsCompletedInSample")


class AdminOutboundRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3900)
    parse_mode: str | None = Field(default=None, alias="parseMode")
    user_id: int | None = Field(default=None, alias="userId")

    model_config = ConfigDict(populate_by_name=True)


class AdminOutboundResult(BaseModel):
    sent: int
    failed: int
    errors: list[str]


class AdminLiveSessionRow(BaseModel):
    """Best-effort “in flight” signal: server still has ``ended_at IS NULL``.

    Telegram does not ping us continuously; freshness is inferred from ``started_at``.
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(serialization_alias="userId")
    name: str
    username: str | None = None
    run_id: str = Field(serialization_alias="runId")
    started_at: datetime = Field(serialization_alias="startedAt")
    presumed_in_game: bool = Field(
        serialization_alias="presumedInGame",
        description="True when started within threshold minutes (still likely playing)",
    )

    @field_serializer("started_at")
    def _serialize_started_at(self, value: datetime) -> str:
        return _utc_iso(value)


class AdminLiveSessionsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    threshold_minutes: int = Field(serialization_alias="thresholdMinutes")
    total_returned: int = Field(serialization_alias="totalReturned")
    caveat: str = Field(
        default="Inferred from open run rows — not socket presence. Older rows are usually crashed clients.",
        description="Explain limitations to dashboard operators.",
    )
    items: list[AdminLiveSessionRow]


class AdminMessageLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime = Field(serialization_alias="createdAt")
    scope: str
    recipient_count: int = Field(serialization_alias="recipientCount")
    success_count: int = Field(serialization_alias="successCount")
    fail_count: int = Field(serialization_alias="failCount")
    recipient_user_id: int | None = Field(serialization_alias="recipientUserId")
    text_preview: str = Field(serialization_alias="textPreview")

    @field_serializer("created_at")
    def _dt(self, value: datetime) -> str:
        return _utc_iso(value)


class AdminMessageLogListResponse(BaseModel):
    items: list[AdminMessageLogPublic]
