# Asteroid Dodger — Backend

FastAPI service that authenticates the Telegram Mini App via HMAC over
`initData`, persists run history, and serves the global leaderboard. Speaks
to a Postgres database in production and to a local SQLite file in dev.

## Endpoints

| Method | Path                | Purpose                                      |
| ------ | ------------------- | -------------------------------------------- |
| GET    | `/health`           | Liveness probe (returns `{ status: "ok" }`). |
| GET    | `/api/me`           | Authenticated player + recent runs.          |
| POST   | `/api/runs/start`   | Mints a server-issued run id.                |
| POST   | `/api/runs/end`     | Finalises a run; updates aggregates.         |
| GET    | `/api/leaderboard`  | Top scores (one entry per user).             |

Every protected endpoint requires the `X-Telegram-Init-Data` header. In
development (`REQUIRE_TELEGRAM_AUTH=false`, the default) a missing header
falls back to a "preview pilot" so you can hit the API from a plain browser.

## Local development

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env       # edit if you want, defaults work out of the box
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000/docs for the auto-generated Swagger UI.

The default `DATABASE_URL=sqlite:///./dev.db` creates `backend/dev.db` on
first boot. Tables are auto-created from the SQLAlchemy models — no manual
migration needed for local work.

## Production deploy (Railway)

1. **Create a Railway project** and add a Postgres plugin.
   `DATABASE_URL` will be injected automatically.
2. **Connect this repo** and point the service root at `backend/`.
   Railway auto-detects Python and uses `Procfile` / `railway.json`.
3. **Set environment variables** in the service's Variables tab:
   - `TELEGRAM_BOT_TOKEN` — same token your bot uses (required).
   - `ALLOWED_ORIGINS` — comma-separated, **no spaces**; include your Mini App
     origin, e.g. `https://galaticadventures.vercel.app` (add
     `http://localhost:5173` only if you need local dev against this deploy).
   - `REQUIRE_TELEGRAM_AUTH=true` — flip on once the Mini App is wired
     so unauthenticated requests are rejected.
   - (Optional) `ANTICHEAT_MIN_RUN_MS`, `ANTICHEAT_MAX_SCORE_PER_SECOND`.
4. **Deploy.** Railway will run `pip install -r requirements.txt` and
   start uvicorn on `$PORT`. The health check at `/health` should be
   green within ~30s.

The service boot calls `Base.metadata.create_all`, which is idempotent — it
creates missing tables on first deploy and is a no-op afterwards. For
schema migrations (Phase 6+), wire up Alembic.

## Anti-cheat

`POST /api/runs/end` rejects submissions that fail any of:

- Duration shorter than `ANTICHEAT_MIN_RUN_MS` (default 2000 ms).
- Client-reported `durationMs` diverging from the server's `now -
  started_at` by more than 30 seconds.
- Score-per-second above `ANTICHEAT_MAX_SCORE_PER_SECOND` (default 80).
- Coins greater than the score, or above ~12% of score.

Rejected runs are deleted (no row left behind) and the API returns 422.
The frontend keeps its optimistic local state in that case, so the player
never sees an error — but the server side stays clean.

## Schema

```
users
  id              BIGINT  PK            -- Telegram user id
  name            STRING
  username        STRING  NULL
  photo_url       STRING  NULL
  language        STRING  NULL
  best_score      INT
  total_coins     INT
  runs_played     INT
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ

runs
  id              STRING  PK            -- server-issued, e.g. "r_aBc123…"
  user_id         BIGINT  FK → users.id
  score           INT
  coins           INT
  duration_ms     INT
  near_misses     INT
  started_at      TIMESTAMPTZ           -- set on /runs/start
  ended_at        TIMESTAMPTZ NULL      -- set on /runs/end
```

Indexes:

- `(user_id, ended_at DESC)` — recent-runs query for `/api/me`.
- `(score DESC)` — fallback for any future "top runs ever" query.
