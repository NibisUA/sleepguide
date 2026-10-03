# SleepGuide

Telegram Mini App for tracking sleep, workouts, stress and screen time, with personal insights.
Full plan: [docs/product.md](docs/product.md).

**Status:** Phase 1–3 — project setup, Telegram authentication, sleep Start/Stop, retroactive entry and editing, Sleep Score with component breakdown, 7/30-day history and a yearly heatmap.

## Stack

- `frontend/` — React + TypeScript + Vite + Tailwind 4 + TanStack Query + react-i18next (uk/en)
- `backend/` — FastAPI + SQLAlchemy 2 (async) + Alembic + PostgreSQL; aiogram 3 bot (webhook) in the same process

## Quick start (local, without Telegram)

```bash
# 1. backend + database
cp backend/.env.example backend/.env
docker compose up --build          # runs migrations, API on http://localhost:8000 (docs: /docs)

# 2. frontend
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

With `ENV=dev` and `DEV_LOGIN_ENABLED=true` the app logs in through `/api/v1/auth/dev`,
so you can use the UI in a normal browser.

## Running inside Telegram

1. Create a bot with [@BotFather](https://t.me/BotFather) and put the token in `backend/.env` as `BOT_TOKEN`.
2. Expose the frontend dev server over HTTPS (Telegram requires it), e.g. `cloudflared tunnel --url http://localhost:5173`.
   The Vite dev server proxies `/api` to the backend, so one tunnel is enough.
3. In `backend/.env` set `MINI_APP_URL=<tunnel url>`. In BotFather set the menu button / Mini App URL to the same address.
4. For the bot's `/start` command, also expose the backend (or set `WEBHOOK_BASE_URL` to a public URL) and set `WEBHOOK_SECRET`.
5. Open the bot in Telegram → **Open SleepGuide**.

Authentication in Telegram: the Mini App sends `initData` to `POST /api/v1/auth/telegram`;
the backend verifies the HMAC signature and `auth_date`, then issues a short-lived JWT.

## Backend development

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
alembic upgrade head                         # needs a running PostgreSQL (see DATABASE_URL)
alembic revision --autogenerate -m "message" # create a new migration
uvicorn app.main:app --reload
```

## API (so far)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/auth/telegram` | Log in with Telegram `initData` |
| GET / PATCH | `/api/v1/me` | Profile, time zone, language, sleep goal |
| POST | `/api/v1/sleep/start` | Start a session (idempotent) |
| POST | `/api/v1/sleep/stop` | Stop; `{ "ended_at": ... }` is required if the session was open > 14 h |
| POST | `/api/v1/sleep` | Retroactive entry (`started_at` + `ended_at`) |
| GET | `/api/v1/sleep/current` | Open session or `null` |
| GET | `/api/v1/sleep?limit=30&date=` | Recent sessions (optionally for one wake-up date) |
| GET | `/api/v1/sleep/{id}` | One session |
| PATCH | `/api/v1/sleep/{id}` | Edit times; also closes a forgotten-Stop session |
| DELETE | `/api/v1/sleep/{id}` | Delete a session (or cancel an open one) |
| GET | `/api/v1/sleep/score/{date}` | Sleep Score + component breakdown for that wake-up date |
| GET | `/api/v1/sleep/history?from=&to=` | Daily summaries for charts and the heatmap (max 367 days) |

Frontend API types: run `npm run gen:api` (backend must be running) to generate them from OpenAPI;
until then `src/types/api.ts` holds hand-written types.

The Sleep Score is computed on the fly (never stored): duration 40, consistency 30, sleep debt 20,
bedtime timing 10. With fewer than 7 days of data the history-dependent components are omitted and
the remaining weights are renormalized, with a "based on limited data" label. Naps (< 3 h) are
stored but excluded from the Score. The breakdown is always shown in the UI.

## Next steps (roadmap Phase 4+)

Bot reminders (evening Start / morning Stop buttons), workout / stress / screen-time modules,
settings, insights and data export.


## Phase 4: bot reminders

- **Evening reminder** (Settings → Bot reminders): a message at the chosen local time with a
  "🌙 Start sleep" button. Sent at most once per day, skipped if a sleep is already running, and
  only within 90 minutes after the scheduled time (never hours late).
- **Morning reminder**: a *silent* message with "☀️ I woke up", only for a session that is still
  open after 5–14 hours, between 07:00 and 12:00 local time, once per session. If the session is
  older than 14 hours the bot asks to confirm the wake-up time in the Mini App.
- **Commands:** `/sleep` (start) and `/wake` (stop) work without opening the Mini App.
- The scheduler is a loop inside the backend process (`app/bot/reminders.py`, checks every minute).
  Run **one** backend process (the default `docker-compose.prod.yml` does). Set
  `REMINDERS_ENABLED=false` to turn it off.
- If the user blocks the bot, their reminders are switched off automatically.
- New migration `0002` (idempotency markers on `users`); it is applied on start.
