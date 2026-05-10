"""Redis-backed cache for ``GET /api/leaderboard`` top rows (shared across replicas).

Caches only the ordered list of ``(user_id, name, best_score)``; per-request
fields ``isSelf`` / ``selfRank`` are still computed in Python and the extra
``self_rank`` DB query when the player is outside the top-N is unchanged.

Invalidation: bump a global generation key when a player sets a new personal
best (see ``bump_leaderboard_generation``). Old cache entries expire via TTL.
"""

from __future__ import annotations

import json
import logging
from typing import Sequence

from .config import get_settings
from .redis_client import get_redis

log = logging.getLogger(__name__)

_GEN_KEY = "lb:gen"


def _top_key(gen: int, limit: int) -> str:
    return f"lb:top:{gen}:{limit}"


def bump_leaderboard_generation() -> None:
    """Invalidate all leaderboard row caches (cheap; works with many limits)."""
    r = get_redis()
    if r is None:
        return
    try:
        r.incr(_GEN_KEY)
    except Exception as exc:
        log.warning("leaderboard cache bump failed: %s", exc)


def try_get_cached_rows(limit: int) -> list[tuple[int, str, int]] | None:
    """Return cached rows or ``None`` on miss / Redis off / error."""
    r = get_redis()
    if r is None:
        return None
    try:
        gen_s = r.get(_GEN_KEY)
        gen = int(gen_s) if gen_s is not None else 0
        raw = r.get(_top_key(gen, limit))
        if raw is None:
            return None
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            return None
        out: list[tuple[int, str, int]] = []
        for row in parsed:
            if (
                isinstance(row, list)
                and len(row) == 3
                and isinstance(row[0], int)
                and isinstance(row[1], str)
                and isinstance(row[2], int)
            ):
                out.append((row[0], row[1], row[2]))
            else:
                return None
        return out
    except Exception as exc:
        log.debug("leaderboard cache read skipped: %s", exc)
        return None


def set_cached_rows(limit: int, rows: Sequence[tuple[int, str, int]]) -> None:
    r = get_redis()
    if r is None:
        return
    ttl = get_settings().redis_leaderboard_ttl_seconds
    payload = [[uid, name, score] for uid, name, score in rows]
    try:
        gen_s = r.get(_GEN_KEY)
        gen = int(gen_s) if gen_s is not None else 0
        r.set(_top_key(gen, limit), json.dumps(payload, separators=(",", ":")), ex=ttl)
    except Exception as exc:
        log.debug("leaderboard cache write skipped: %s", exc)
