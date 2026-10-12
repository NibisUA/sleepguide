# SleepGuide

> Phase 11 + рекорди, серії, історія 90/ALL та персональні функції (12.10.2026).
> Актуальні команди, перевірки та кроки перед production: [docs/RELEASE.md](docs/RELEASE.md).
> Нові функції й міграція 0008: [docs/RECORDS_AND_STREAKS.md](docs/RECORDS_AND_STREAKS.md).
> Діапазони історії та пагінація: [docs/HISTORY_RANGES.md](docs/HISTORY_RANGES.md).
> OCR, тренди, нагадування, цілі, картки та перевірка калібрування: [docs/PERSONAL_PROGRESS.md](docs/PERSONAL_PROGRESS.md).

Telegram Mini App for tracking sleep, workouts, stress and screen time, with personal insights.
Full plan: [docs/product.md](docs/product.md).

**Status:** Phases 1–11, records/streaks, full history, local screenshot OCR, personal baselines, pattern reminders, achievements/weekly goals and shareable PNG cards are available. Morning feedback and an offline calibration evaluator are implemented; empirical calibration awaits real data and weights remain v1.0. 244 backend / 40 frontend tests pass locally. Head 0009, export 1.2. Production release, policy review and real-device checks remain pending. See [docs/STATUS.md](docs/STATUS.md).

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

Frontend API types are generated from `docs/openapi.json`: run `python scripts/export_openapi.py`
from backend, then `npm run gen:api` from frontend. A running API is only needed for `gen:api:live`.

The Sleep Score is computed on the fly (never stored): duration 40, consistency 30, sleep debt 20,
bedtime timing 10. With fewer than 7 days of data the history-dependent components are omitted and
the remaining weights are renormalized, with a "based on limited data" label. Naps (< 3 h) are
stored but excluded from the Score. The breakdown is always shown in the UI.

## Current extension

Workout History → Exercises records strength sets or distance efforts. All-time records appear
below workouts; Home shows current/best logging streaks. JSON export 1.1 and account deletion
cover new data. See [docs/RECORDS_AND_STREAKS.md](docs/RECORDS_AND_STREAKS.md).


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


## Phase 5: workouts

- **Home → Workout:** pick a type (gym, home, running, football, walking, other) and press
  "Start workout"; a stopwatch runs, the intensity (easy / moderate / hard / very hard) can be
  set while training or when finishing. A workout running longer than 6 hours asks for the real
  end time (like the 14-hour rule for sleep); "Discard workout" removes a mistaken start.
- **History → Workouts:** count, total time, minutes-per-day chart (7 / 30 days), list with
  edit / delete and "Add workout" for forgotten sessions. Overlaps between workouts are rejected,
  a workout is limited to 6 hours, and its day is the local date of its **start**.
- **API** (`/api/v1/workouts`): `POST /start`, `POST /stop`, `GET /current`, `GET /history?from&to`,
  `POST` (retroactive), `GET` (list), `GET/PATCH/DELETE /{id}`. Errors use the same
  `{"detail": {"code": ...}}` shape (`no_running_workout`, `end_time_required`, `overlap`, `too_long`,
  `invalid_time`, `workout_not_found`).
- Workouts do not produce a score; they are an input for the insights planned in Phase 9.
- Migration `0003` creates the `workouts` table (one running workout per user is enforced by a
  partial unique index).


## Phase 6: stress

- **Home → Stress:** one tap on 1-5 logs a rating immediately (no other input needed). A small
  panel then offers an optional reason (university, work, relationships, money, sleep, training,
  personal, other) and "Undo"; the card also shows today's average and number of ratings.
- **History → Stress** (7 / 30 days): average, peak and number of ratings, a daily-average chart
  (bars colored green / amber / red, a tick marks the day's peak), the list of ratings with edit
  and delete, and "Add entry" for a rating you forgot (the time can be changed, never the future).
- A user can log several ratings per day; the day value is their average (one decimal) and the
  maximum is kept for "high-stress day" detection in the insights (Phase 9).
- **API** (`/api/v1/stress`): `POST` (only `level` is required), `GET` (`from`, `to`, `limit`),
  `GET /history?from&to` (per-day count, average, max, sum for every day of the range),
  `GET/PATCH/DELETE /{id}`. `PATCH` with `"category": null` clears the reason; omitted fields keep
  their value. Errors: `stress_not_found`, `invalid_time`, `invalid_range`.
- Migration `0004` creates `stress_logs` (the level is restricted to 1-5 by a CHECK constraint).


## Phase 7: Screen Time and personal API tokens

- **Home → Screen Time:** today's and yesterday's numbers and a form with two fields (total for the
  day and phone use in the 2 hours before bed, each as hours + minutes). Any day of the last year
  can be logged; saving a day again replaces it. Apple does not let apps read Screen Time, so the
  numbers are typed in (or sent by a Shortcut, see below).
- **History → Screen Time** (7 / 30 days): averages, days with data, a bar chart (amber = before
  bed), the list with edit / delete (records sent by a Shortcut are marked).
- **Settings → Integrations:** create / revoke personal API tokens (max 10 active). A token is shown
  **once**; only its SHA-256 digest is stored. Step-by-step iOS setup: `shortcuts/README.md`.
- **API:** `PUT /api/v1/screen-time/{YYYY-MM-DD}` (idempotent upsert; `total_minutes` 0-1440,
  `before_bed_minutes` 0-120 and never above the total, day within the last year),
  `GET /api/v1/screen-time?from&to`, `DELETE /api/v1/screen-time/{day}`;
  `POST/GET /api/v1/me/api-tokens`, `DELETE /api/v1/me/api-tokens/{id}`.
- **Token scope:** a token is accepted only by `POST /sleep/start`, `POST /sleep/stop` and
  `PUT /screen-time/{day}` (those records get `source: "shortcut"`). It cannot read data or manage
  tokens: every other endpoint accepts only the Mini App session.
- **Rate limits** (in memory, single process): 10 failed token attempts per IP per 5 minutes and
  120 requests per token per minute (`429 rate_limited`).
- Migration `0005` creates `screen_time_daily` (unique per user and day, CHECK constraints) and
  `api_tokens`.


## Phase 8: Daily Summary and dashboard completion

- **`GET /api/v1/days/{YYYY-MM-DD}`** (session JWT only; never the future): sleep Score of the night
  that ended on that day and the day's finished sleep sessions (naps included), finished workouts
  with their total minutes, stress (count / average / max and the ratings) and Screen Time. All four
  areas are always present: empty ones come back empty (`null` / `[]` / `count: 0`).
- **Home:** three tiles for today (workouts, stress average, screen time); tapping them opens the
  Daily Summary. A round **+** button in the middle of the tab bar opens a quick-add sheet
  (sleep / workout / stress / screen time) that scrolls to the matching card and highlights it.
- **History:** the selected day (tap a cell of the yearly heatmap) has a "Day summary" button that
  opens the same sheet; inside it you can step to the previous / next day.
- **Insights tab:** a placeholder with a progress bar (nights of sleep data out of 14) and the
  topics the analysis will cover; the rules themselves arrive in Phase 9.
- After any successful write the aggregated `["days"]` queries are refreshed (one `MutationCache`
  handler in `App.tsx`), so tiles and the summary never lag behind the module cards.
- No database changes in this phase (no new migration).
