# Telegram Bot + 3D Asteroid Dodger Mini App

A small monorepo that contains:

- **`/` (root)** — a Python Telegram bot built with
  [`python-telegram-bot`](https://docs.python-telegram-bot.org/) v21. It
  exposes `/start`, `/help`, `/menu`, `/about`, and `/play`.
- **`/webapp`** — a 3D **Asteroid Dodger** Telegram Mini App built with React
  18, TypeScript, Vite, Tailwind, and `@react-three/fiber`. Drag anywhere to
  fly, dodge the neon storm, grab glowing coin pickups, score near-miss
  bonuses, and survive longer to earn more coins.

The bot acts as the *launcher*: pressing the **Play** button on `/start` (or
sending `/play`) opens the React Mini App **inside** Telegram, where the
verified user identity, theme colors, haptics, and main button are wired up
through the Telegram WebApp SDK.

```
┌──────────────┐   /start (Play)    ┌────────────────────────────┐
│ Telegram app │ ─────────────────▶ │ Mini App on Vercel (HTTPS) │
└──────────────┘                    │  React + r3f + TS          │
       ▲                            │  Asteroid Dodger game      │
       │   webhook / polling        └────────────────────────────┘
       ▼
┌──────────────┐
│  Python bot  │  ← bot.py, handlers/
└──────────────┘
```

---

## 1. Prerequisites

- **Python 3.11+** (tested with 3.13)
- **Node.js 20+** and **npm** (tested with Node 22)
- A Telegram account
- A free **Vercel** account (or any HTTPS static host)

## 2. Get a bot token from @BotFather

1. Open Telegram and search for **@BotFather** (the official one has a blue check).
2. Start a chat and send `/newbot`.
3. Choose a **display name** (e.g. `Asteroid Dodger Bot`).
4. Choose a **username** ending in `bot` (e.g. `my_asteroid_dodger_bot`). It
   must be unique.
5. BotFather replies with an HTTP API token like `123456789:AAH...XYZ`.
   Keep this secret — anyone with it can control your bot.

Optional, also in BotFather:

- `/setdescription` — short text shown on the bot's profile.
- `/setcommands` — paste this so users see command suggestions:
  ```
  start - Greet and show the menu
  play - Launch the Asteroid Dodger Mini App
  menu - Show the inline-button menu
  about - Learn about this bot
  help - Show available commands
  ```

## 3. Run the bot locally

From the repo root:

```powershell
# create + activate a venv (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# install deps
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# configure secrets
Copy-Item .env.example .env
notepad .env   # paste your bot token next to TELEGRAM_BOT_TOKEN
               # leave WEBAPP_URL empty for now

# run
python bot.py
```

You should see `Bot is starting. Press Ctrl+C to stop.` In Telegram, find your
bot by its `@username` and send `/start`. You'll see the menu, but the
**Play** button won't appear yet — it requires `WEBAPP_URL` to be a real
HTTPS URL.

## 4. Run the Mini App locally (preview mode)

```powershell
cd webapp
npm install
npm run dev
```

This starts Vite at `http://localhost:5173/`. Open it in any browser to see
the game's "preview mode" — the Telegram SDK gracefully no-ops outside
Telegram, so you can play with mouse + WASD/arrows.

> **Note:** Telegram itself **rejects `http://` URLs** for Mini Apps. To open
> the game *inside* Telegram during development, see §6 (ngrok) or skip
> straight to deploying on Vercel (§5).

Useful scripts:

| Command            | What it does                            |
| ------------------ | --------------------------------------- |
| `npm run dev`      | Vite dev server with HMR                |
| `npm run build`    | Type-check (`tsc -b`) + production build|
| `npm run preview`  | Serve the production `dist/` locally    |
| `npm run typecheck`| Just type-check                         |

## 5. Deploy the Mini App to Vercel

The fastest path is the **Vercel CLI** (no GitHub required):

```powershell
cd webapp
npm i -g vercel
vercel login           # one-time browser auth
vercel --prod          # first run prompts for project name; pick something
```

Or push the repo to GitHub and import it on
[vercel.com/new](https://vercel.com/new). Vercel auto-detects Vite and uses
the `webapp/` directory as the project root if you set the **Root Directory**
to `webapp` in project settings.

After the deploy succeeds, copy the `https://<project>.vercel.app` URL.

### Wire the deployed Mini App to your API (Stats / Leaderboard)

The game works offline, but **global stats and leaderboard** need your FastAPI
backend reachable from the browser.

1. **Vercel** — open the project → **Settings** → **Environment Variables**:
   - **Name:** `VITE_API_BASE_URL`
   - **Value:** your public API root, e.g. `https://your-service.up.railway.app`
     (no trailing slash).
   - Save, then trigger a **new deployment** (Production) so Vite bakes the
     value into the client bundle.

2. **Railway** (the FastAPI service) → **Variables**:
   - **Name:** `ALLOWED_ORIGINS`
   - **Value:** include your live Mini App origin, for example:
     `https://galaticadventures.vercel.app`
   - You can list several origins separated by commas (no spaces), e.g. add
     `http://localhost:5173` if you still test the API locally against the same
     deploy.

If the browser blocks requests with a CORS error, `ALLOWED_ORIGINS` on Railway
does not match the exact origin shown in the address bar (scheme + host + port).

## 6. Wire the bot to the Mini App

1. Paste the Vercel URL into `.env` (in the **repo root**, not `webapp/`):
   ```
   WEBAPP_URL=https://your-project.vercel.app
   ```
2. **Register the Mini App** with BotFather:
   - Send `/newapp`, pick your bot, set a short name like `dodger`, paste the
     Vercel URL, then upload a 640×360 preview image (any neon screenshot of
     the game works).
   - Optionally `/setmenubutton` → pick your bot → enter `Play` and the
     Vercel URL. This adds a permanent "Play" button to the bot's chat.
3. **Restart the bot** (`Ctrl+C`, then `python bot.py`).
4. In Telegram, send `/start` to your bot. You should now see a
   **🚀 Play Asteroid Dodger** button. Tap it — the game opens inside
   Telegram.

### Tunneling for local dev (alternative to Vercel during development)

If you'd rather iterate against a local dev server, tunnel it via
[ngrok](https://ngrok.com/) or
[cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/):

```powershell
# in one terminal
cd webapp ; npm run dev

# in another
ngrok http 5173
```

Copy the `https://...ngrok-free.app` URL into `WEBAPP_URL`, restart the bot,
and you can hot-reload changes while testing inside Telegram.

---

## 7. Project layout

```
telegram_project/
├── bot.py                  # entry: logging, app builder, run_polling
├── config.py               # typed Settings: bot_token, log_level, webapp_url
├── requirements.txt        # python-telegram-bot, python-dotenv
├── .env.example            # TELEGRAM_BOT_TOKEN, LOG_LEVEL, WEBAPP_URL
├── handlers/
│   ├── __init__.py         # registers every handler
│   ├── commands.py         # /start /help /menu /about /play + error handler
│   ├── messages.py         # echoes any plain-text message
│   └── callbacks.py        # inline-keyboard button presses
└── webapp/                 # Vite + React + TS Mini App
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── vercel.json
    ├── index.html          # loads telegram-web-app.js + #root
    └── src/
        ├── main.tsx        # bootstrap
        ├── App.tsx         # phase-driven layout
        ├── index.css       # neon palette, scanlines, vignette
        ├── global.d.ts     # window.Telegram type augmentation
        ├── telegram/
        │   └── sdk.ts      # ready/expand, theme, haptics, MainButton, swipes
        ├── game/
        │   ├── refs.ts     # mutable Vector3s shared by input + frame loop
        │   ├── store.ts    # zustand: phase, score, bestScore, totalCoins
        │   ├── events.ts   # zustand: transient toast events (+50 / +10)
        │   ├── controls.ts # drag-anywhere XY + WASD/arrows
        │   ├── physics.ts  # collision + near-miss + pickup checks
        │   ├── Scene.tsx   # <Canvas> root, lights, fog, Stars
        │   ├── Ship.tsx    # neon ship, idle bob, banking on movement
        │   ├── AsteroidField.tsx  # pooled spawner + near-miss detection
        │   ├── CoinField.tsx      # glowing tori + magnet + burst pool
        │   └── GameLoop.tsx       # +1 score every 100 ms while playing
        └── ui/
            ├── Stat.tsx          # glowing stat number
            ├── StartScreen.tsx   # title, best/coins, "Tap to start"
            ├── Hud.tsx           # in-game score chip
            ├── GameOver.tsx      # score / best / +coins, Play again
            └── ToastLayer.tsx    # floating "+50" / "+10 near miss" toasts
```

## 8. How the game scores

- **+1 every 100 ms** of survival → `score`.
- **+50 per coin pickup** — golden glowing tori spawn in the asteroid stream.
  When a coin is close in XY and roughly aligned in Z, a gentle magnetic pull
  helps you grab it; collecting one fires a light haptic, an expanding amber
  ring burst in 3D, and a floating "+50" toast.
- **+10 per near-miss** — when an asteroid passes the ship's plane just
  outside the collision boundary (within ~0.7 world units), you earn a
  bonus and see a "+10 NEAR MISS" toast in cyan. Each asteroid can only
  trigger this once.
- On collision: `coinsEarned = floor(score / 10)` is added to a persistent
  `totalCoins`, and `bestScore` updates if the run was a record.
- All values persist to **`localStorage`** under the key `asteroid-dodger:v1`.
  This is **not** secure — see §10 for the planned backend.

## 9. Controls

- **Mobile / touch** — drag anywhere on the screen. The ship's target offsets
  by the same fraction of the screen your finger has moved since touch-down.
  Vertical swipes that would normally close the Mini App are disabled while
  playing (Bot API 7.7+; older clients fall back to a regular swipe).
- **Desktop / keyboard** — `←` / `→` / `↑` / `↓` or `WASD`.

## 10. What's next (planned phases)

Implemented so far: **Phases 0–5** (bot, Mini App, game, backend in `backend/`
with FastAPI + Postgres path). See §11 for Railway deploy.

Still optional / polish:

- **Phase 6 — streaks, invites, refinements.** Daily bonus, invite links, Alembic migrations, optional second Railway service for the bot.

## 11. Deploy the FastAPI backend to Railway (backend + bot, no `webapp/`)

The Mini App on Vercel can stay in [its own GitHub repo](https://github.com/banderGlitch/galaticadventures).  
Put **everything else** (this folder minus `webapp/`) in a **second repo** for Railway and the bot.

### 11.1 One-time: Git repo without `webapp/`

The root `.gitignore` lists `/webapp/`, so the frontend folder is ignored when you commit from `telegram_project/`.

```powershell
cd path\to\telegram_project
git init
git branch -M main
git add .
git status   # should list backend/, bot.py, handlers/, config.py, etc. — not webapp/
git commit -m "Initial: FastAPI backend + Telegram bot"
```

Create an empty repo on GitHub (this project uses
[`banderGlitch/telegrambackend`](https://github.com/banderGlitch/telegrambackend)), then:

```powershell
git remote add origin https://github.com/banderGlitch/telegrambackend.git
git push -u origin main
```

Keep using the existing `webapp/` clone for Vercel; you do not need to delete it locally.

### 11.2 Railway: API service (FastAPI)

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub** → pick the **backend** repo.
2. **Settings** → **Root Directory** → set to: `backend`  
   (so Railway runs `pip install -r requirements.txt` and the `Procfile` in that folder).  
   **Optional:** leave Root Directory empty — the repo root `requirements.txt`
   and `Procfile` then install backend deps and run `python -m uvicorn` from
   `backend/` (two valid setups; `backend` as root is still the cleanest).

3. **Add** a **PostgreSQL** database; Railway injects `DATABASE_URL` into the service.
4. **Variables** (on the **same** service as the API):

   | Variable | Example / notes |
   | ---------- | ---------------- |
   | `TELEGRAM_BOT_TOKEN` | Same token as your bot (for `initData` HMAC). |
   | `ALLOWED_ORIGINS` | `https://galaticadventures.vercel.app` (comma-separated, no spaces; add `http://localhost:5173` only if needed). |
   | `REQUIRE_TELEGRAM_AUTH` | `true` in production. |
   | `LOG_LEVEL` | `INFO` |

5. **Deploy** → open the generated **public URL** (e.g. `https://xxx.up.railway.app`).
6. **Health check:** open `https://<your-url>/health` — should return `{"status":"ok"}`.
7. In **Vercel** (Mini App project): set `VITE_API_BASE_URL` to that same origin (no trailing slash), then **redeploy**.

Details: `backend/README.md`.

### 11.3 Optional: run the Telegram bot on Railway

The bot is **not** the same process as FastAPI. If you want **polling** on Railway:

- Add a **second** Railway service from the **same** GitHub repo.
- **Root Directory:** leave empty or set to repo root (where `bot.py` lives).
- **Start command:** `python bot.py`
- Install deps: Railway/Nixpacks may need a `requirements.txt` at repo root (you already have one for the bot) or a `nixpacks.toml` pointing to it.

Many people run `bot.py` on a home PC or a tiny VPS instead, and only host the API on Railway.

### 11.4 Security

- Never commit `.env` (tokens). Use Railway **Variables** only for secrets.
- Rotate the bot token if it was ever committed or pasted in chat.

## 12. Troubleshooting

- **`uvicorn: command not found` on Railway** — the deploy image only had the
  old root deps (bot only). Fix: set **Root Directory** to `backend` and
  redeploy; **or** pull the latest `telegrambackend` repo — root
  `requirements.txt` now includes `backend/requirements.txt`, the root
  `Procfile` starts uvicorn from `backend/`, and start commands use
  `python -m uvicorn`. Trigger a fresh deploy after updating.

- **`TELEGRAM_BOT_TOKEN is not set`** — copy `.env.example` to `.env` and
  paste your token.
- **Play button doesn't show on `/start`** — `WEBAPP_URL` must start with
  `https://`. The bot intentionally hides the button if it doesn't.
- **Telegram opens an empty white page** — check that the Vercel URL works
  in a normal browser first; verify the HTTPS cert is valid.
- **`Bot was not modified` / `Conflict: terminated by other getUpdates`** —
  another instance of the bot is already polling with the same token. Stop
  one of them.
- **Asteroid Dodger feels laggy on a low-end Android** — drop the asteroid
  pool size (`POOL` constant in `webapp/src/game/AsteroidField.tsx`) from
  `40` down to `25`.
- **PowerShell can't activate the venv** — run
  `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
  once.
