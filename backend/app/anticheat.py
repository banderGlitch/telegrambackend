"""Plausibility checks applied to every `/runs/end` submission.

The goal here isn't bulletproof security — that's impossible without server
authoritative simulation — it's to make the leaderboard *plausible*. A bored
teen wiring a curl command to submit `{score: 999999}` should bounce. We're
optimising for "raises the bar enough to not pollute the social leaderboard".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


# Coins are paid as `floor(score / 10)` on the client. Allow a tiny tolerance
# for rounding/edge cases (off-by-one is fine; 2× is not).
COINS_MAX_RATIO_OF_SCORE = 0.12  # 12% of score


@dataclass(frozen=True)
class AntiCheatVerdict:
    accepted: bool
    reason: str | None = None


def evaluate_run(
    *,
    score: int,
    coins: int,
    duration_ms: int,
    started_at: datetime,
    now: datetime,
    min_run_ms: int,
    max_score_per_second: int,
) -> AntiCheatVerdict:
    """Return whether a submitted run is plausible.

    Checks (cheapest first; short-circuit on first failure):

    1. **Duration floor** — runs shorter than `min_run_ms` aren't long enough
       for any real score to accrue.
    2. **Server clock cross-check** — the duration the client claims must
       agree, within a generous tolerance, with `now - started_at`. Catches
       clients that lie about duration to inflate score-per-second.
    3. **Score per second** — hard ceiling. Even a perfect player can't earn
       more than ~`max_score_per_second` points per second given the
       difficulty curve.
    4. **Coin sanity** — coins ≤ score and coins ≤ score × ratio.
    """
    # 1) Minimum duration.
    if duration_ms < min_run_ms:
        return AntiCheatVerdict(False, f"duration {duration_ms}ms < floor {min_run_ms}ms")

    # 2) Cross-check client duration against server clock.
    if started_at.tzinfo is None:
        # SQLite forgets timezones; assume UTC.
        started_at = started_at.replace(tzinfo=timezone.utc)
    server_elapsed_ms = int((now - started_at).total_seconds() * 1000)
    # 30s tolerance covers network jitter, browser throttling, render hitches.
    if abs(server_elapsed_ms - duration_ms) > 30_000:
        return AntiCheatVerdict(
            False,
            f"client duration {duration_ms}ms diverges from server {server_elapsed_ms}ms",
        )

    # 3) Score-per-second cap.
    duration_seconds = max(1.0, duration_ms / 1000.0)
    score_per_second = score / duration_seconds
    if score_per_second > max_score_per_second:
        return AntiCheatVerdict(
            False,
            f"score-per-second {score_per_second:.1f} exceeds cap {max_score_per_second}",
        )

    # 4) Coin sanity.
    if coins > score:
        return AntiCheatVerdict(False, f"coins {coins} exceed score {score}")
    if coins > score * COINS_MAX_RATIO_OF_SCORE + 5:  # +5 absolute slack
        return AntiCheatVerdict(
            False,
            f"coins {coins} exceed plausible {COINS_MAX_RATIO_OF_SCORE:.0%} of score {score}",
        )

    return AntiCheatVerdict(True)
