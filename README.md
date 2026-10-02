# SleepGuide

Telegram Mini App for tracking sleep, workouts, stress and screen time, with personal insights.
Full plan: [docs/product.md](docs/product.md).

**Status:** Phase 1–2 — project setup, Telegram authentication, sleep Start/Stop vertical slice.

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
| GET | `/api/v1/sleep/current` | Open session or `null` |
| GET | `/api/v1/sleep?limit=30` | Recent sessions |

Frontend API types: run `npm run gen:api` (backend must be running) to generate them from OpenAPI;
until then `src/types/api.ts` holds hand-written types.

## Next steps (roadmap Phase 3+)

Retroactive sleep entry and editing, Sleep Score, bot reminders, workout / stress / screen-time modules,
dashboard and history, insights.
