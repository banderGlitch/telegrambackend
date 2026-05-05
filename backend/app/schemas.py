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
