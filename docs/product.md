# SleepGuide — Product & Development Plan (v2)

> **Стан 12.10.2026:** поточний обсяг і правила — у [RELEASE.md](RELEASE.md) та [STATUS.md](STATUS.md).
> Цей v2-план є історичним. Після Phase 11 додані рекорди вправ і серії записів:
> [RECORDS_AND_STREAKS.md](RECORDS_AND_STREAKS.md). Heatmap та інсайти вже існують,
> API-типи генеруються. Решта пост-MVP ідей відкладена.
> Історія 90/ALL та пагінація також реалізовані: [HISTORY_RANGES.md](HISTORY_RANGES.md).

> Telegram Mini App + Backend (FastAPI) + iOS Shortcuts integration

## Changelog v1 → v2

- **Recovery Score removed.** Without HRV / heart-rate data it was an arbitrary weighted sum, and workouts contributed positively to "recovery", which is misleading. The core of the product is now **Sleep Score** plus personal **Insights**.
- **No native iOS app, no Swift.** Apple's Screen Time API does not let an app export usage totals to its own backend (the report extension is sandboxed) and needs a special entitlement. Screen Time is entered **manually or via iOS Shortcuts**.
- **Sleep is logged with Start / Stop buttons** (evening / morning), with handling for forgotten Stop and a bot reminder.
- **Insights appear only after enough data** (explicit thresholds), plus a demo mode with seed data.
- **Simplified architecture:** no Repositories layer, bot runs inside the backend process, TypeScript types generated from OpenAPI (Zod dropped).
- **Data model fixed:** `local_date`, nullable `ended_at`, one open sleep session, multiple stress logs per day, `exercises` table, idempotent screen-time upsert, user settings, no stored scores.
- **MVP scope reduced:** Records / PRs, yearly heatmap, gamification and the "Progress" tab moved to post-MVP. A daily reminder from the bot moved **into** MVP (retention).
- **Localization** (uk / en) built in from day one.
- Privacy basics (delete / export data) moved earlier in the roadmap.

---

## 1. Product concept

SleepGuide is a personal lifestyle tracker built around four areas:

- 🌙 Sleep
- 🏋️ Workout
- 📱 Screen Time
- 🧠 Stress

It combines them in one daily view and uses the user's own history to find personal patterns ("what affects my sleep?").

The product should feel closer to a polished mobile app (Somnr-style) than to a traditional Telegram bot.

### Main principles

1. **Minimal manual effort.** Every log should take seconds; automate what can be automated (Shortcuts, bot reminders).
2. **Honest numbers.** No fake precision. Do not claim what the data cannot support (e.g. no "recovery" without physiological data).
3. **Explainable.** Every score and every insight shows what it is based on.
4. **Consistency over perfection.**

### What the Home screen answers

1. How did I sleep?
2. What have I logged today?
3. What patterns has the app found in my data?

---

## 2. Architecture

```text
   iOS Shortcuts (optional)            TELEGRAM
   Sleep Focus on/off,                    │
   screen-time form  ─────┐               ▼
                          │      ┌──────────────────┐
                          │      │  Telegram Bot    │  (aiogram, webhook,
                          │      │  reminders,      │   same process as
                          │      │  Mini App launch │   backend)
                          │      └────────┬─────────┘
                          │               │ Open Mini App
                          │               ▼
                          │      ┌──────────────────┐
                          │      │  Telegram Mini   │
                          │      │  App (React+TS)  │
                          │      └────────┬─────────┘
                          │               │ HTTPS (JWT)
                          ▼               ▼
                   ┌────────────────────────────┐
                   │   Backend — FastAPI        │
                   │   (API token for Shortcuts,│
                   │    Telegram auth for app)  │
                   └────────────┬───────────────┘
                                ▼
                          PostgreSQL
```

## 3. Languages and technology stack

Languages used in the project:

- **TypeScript** — Mini App
- **Python** — backend and bot
- **SQL** — PostgreSQL (migrations via Alembic, written in Python)
- Configuration only: YAML / Dockerfile. Shortcuts are built visually (no code).

### Frontend

- React, TypeScript, Vite
- Tailwind CSS
- Telegram Mini Apps SDK
- Recharts (or another chart library)
- TanStack Query for server state
- React Router if multiple routed screens are needed
- `react-i18next` for localization (uk / en)
- API types generated from the backend OpenAPI schema (e.g. `openapi-typescript`) — single source of truth, no Zod duplication of Pydantic models

### Backend

- Python, FastAPI, Pydantic
- SQLAlchemy 2 + Alembic
- PostgreSQL
- aiogram 3 (bot, webhook mode, mounted in the same FastAPI app)
- Redis only if a real need appears (rate limiting, queues)

### Infrastructure

- Frontend: Vercel (or any static hosting)
- Backend: Railway / Render / similar, managed PostgreSQL
- GitHub for source control, basic CI (lint + tests)
- Telegram Mini Apps require HTTPS, so use a tunnel (e.g. Cloudflare Tunnel / ngrok) in local development

The exact hosting provider can be decided later.

---

## 4. Repository structure

```text
sleepguide/
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── sleep/
│   │   │   ├── workout/
│   │   │   ├── stress/
│   │   │   ├── screen-time/
│   │   │   ├── dashboard/
│   │   │   ├── insights/
│   │   │   └── settings/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── locales/          # uk.json, en.json
│   │   ├── services/
│   │   ├── types/            # generated API types
│   │   └── styles/
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/             # config, auth, security
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic
│   │   ├── services/         # business logic (uses the SQLAlchemy session directly)
│   │   ├── analytics/        # sleep score, insight rules
│   │   ├── bot/              # aiogram handlers, keyboards, reminders
│   │   ├── seed/             # demo data generator
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   ├── pyproject.toml
│   └── .env.example
│
├── shortcuts/                # exported iOS Shortcuts + setup instructions
├── docs/
│   ├── product.md
│   ├── architecture.md
│   ├── api.md
│   ├── database.md
│   └── design.md
│
├── .gitignore
├── README.md
└── docker-compose.yml
```

---

## 5. Frontend plan

### 5.1 Main navigation

Four primary areas:

```text
Home
History
Insights
Settings
```

A central `+` action opens quick logging:

```text
+ Add

🌙 Sleep   (Start / Stop)
🏋️ Workout
🧠 Stress
📱 Screen Time
```

Screen Time is entered manually here, or sent automatically by an iOS Shortcut.

### 5.2 Feature structure

Each feature contains its own UI and logic:

```text
features/
├── sleep/
│   ├── components/
│   ├── hooks/
│   ├── api.ts
│   └── utils.ts
├── workout/
├── stress/
├── screen-time/
├── dashboard/
├── insights/
└── settings/
```

Avoid giant components.

### 5.3 Localization

- Languages: Ukrainian and English from the start.
- Default language from Telegram `language_code`, changeable in Settings.
- No hard-coded strings in components; all texts via i18n keys.
- Insight texts are stored as **key + parameters** (e.g. `insight.screen_before_bed.sleep_shorter`, `{minutes: 24}`), never as final strings.
- Dates, times and durations formatted with `Intl`.

---

## 6. Home / Today screen

The most important screen. The hero element is the Sleep Score.

```text
Good morning

Sleep Score
     91
   9h 46m

Today
Workout       1h 12m · Hard
Screen Time   5h 18m
Stress        2 / 5
```

Below:

```text
Latest insight

You sleep 24 minutes less on days when
screen time before bed exceeds 60 minutes.
```

If there is not yet enough data for insights, show a progress hint instead ("Insights unlock after 14 days of data — 5 / 14").

If a sleep session is currently open, the top of the screen shows the running session with a **Stop** button.

---

## 7. Sleep module

### 7.1 MVP: Start / Stop

- **Start sleep** in the evening → creates an open session.
- **Stop** in the morning → closes it, computes duration, shows the Sleep Score.
- Manual edit of bedtime / wake-up time at any moment (needed for forgotten taps).
- Sleep goal (default 8 h, editable in Settings).
- Sleep history.

### 7.2 Forgotten Stop

- If a session stays open longer than **14 hours**, the next app open / bot message asks: *"When did you wake up?"* with a time picker. The duration is not counted until the user confirms.
- Sessions can also be created retroactively ("I forgot to press Start").

### 7.3 Bot reminders (part of MVP)

- Evening reminder with an inline button: **"🌙 Start sleep"** — the user can start the session without opening the Mini App (fewer screen minutes right before bed).
- Morning message (if a session is open): **"☀️ I woke up"** button.
- Reminder times are configurable in Settings and can be turned off.

### 7.4 iOS Shortcuts (optional automation)

- A Shortcuts automation on **Sleep Focus on / off** calls `POST /api/v1/sleep/start` and `POST /api/v1/sleep/stop` with a personal API token.
- The user creates the token in Settings → "Integrations" (shown once, can be revoked).
- Reading sleep samples from Apple Health via Shortcuts and sending them to the backend is a post-MVP idea.

### 7.5 Sleep sessions rules

- A sleep session belongs to the **local date of the wake-up** (`local_date`).
- Naps (sessions shorter than ~3 h) are stored, but excluded from Sleep Score by default.
- Only one open session per user at a time.
- Time zone comes from `users.timezone`; store timestamps in UTC and compute `local_date` on write.

---

## 8. Sleep Score

Sleep Score is the only composite score in the product.

Components (weights configurable in backend code, not final):

```text
Duration        40   — vs. the user's sleep goal
Consistency     30   — regularity of bedtime and wake-up over recent days
Sleep debt      20   — accumulated deficit over the last 7 days
Bedtime timing  10   — not too late relative to the user's target
```

Example:

```text
Sleep Score: 89

Duration        37/40
Consistency     25/30
Sleep debt      18/20
Bedtime timing   9/10
```

### Cold start

- Consistency and sleep debt need history. With fewer than **7 days** of sleep, these components are omitted and the score is computed from the remaining components (weights renormalized), with a small "based on limited data" label.
- The score is computed on the fly from sessions (not stored). If it becomes slow, add a cache table with an `algorithm_version` column.

### Explainability

The Sleep Score screen always shows the component breakdown.

---

## 9. Workout module

Intentionally simple.

### Quick Workout

```text
Start Workout

Type:      Gym · Home · Running · Football · Walking · Other
Intensity: Easy · Moderate · Hard · Very Hard
```

- Starting a workout creates a timer; finishing it saves duration, type and intensity.
- Workouts can also be added retroactively.
- Workout history with edit / delete.
- Workouts do **not** produce any score. They are used in Insights (e.g. sleep on days after workouts) and in History graphs.

> Records / PRs are moved to post-MVP (see section 23).

---

## 10. Stress module

Logging must take a few seconds.

```text
1 — Very low
2 — Low
3 — Moderate
4 — High
5 — Very high
```

- Multiple logs per day are allowed (each has a timestamp).
- The day's stress value = average of the day's logs (max is also stored for "high-stress day" detection).
- Optional category: University, Work, Relationships, Money, Sleep, Training, Personal, Other.
- The app never forces the user to explain why they are stressed.

---

## 11. Screen Time

### Approach

Apple's Screen Time API (Family Controls / DeviceActivity) does not allow exporting usage totals to an app's own backend, and requires a special entitlement. Therefore **no native iOS app** and **no automatic import** in this product.

Two input methods:

1. **Manual form** in the Mini App (two numbers, ~5 seconds).
2. **iOS Shortcut** that prompts for the numbers (or reminds the user) and sends them via `POST /api/v1/screen-time` with the personal API token.

### Fields

- `total_minutes` — total screen time for the day
- `before_bed_minutes` — phone use in the ~2 hours before going to bed (user's estimate)

### Notes

- One record per user per day; a repeated submission **updates** the record (idempotent upsert).
- Category-level data is not collected in the MVP.
- Screen Time does not affect Sleep Score directly. It is used only in Insights and History.
- Optional idea for later: parse a screenshot of the iOS Screen Time page with a vision model.

---

## 12. History

Time ranges:

```text
7D | 30D | 90D | ALL
```

- **Sleep:** score, duration, bedtime, wake-up time
- **Screen Time:** total, average, trend, before-bed minutes
- **Stress:** daily average, high-stress days
- **Workout:** count, total time, intensity

MVP includes 7D and 30D and a simple month calendar (colored by sleep score / duration). Tapping a day opens its Daily Summary. 90D / ALL and the yearly heatmap are post-MVP.

---

## 13. Daily Summary

A unified view of one day:

```text
September 30

Sleep
8h 42m · Score 91

Workout
1h 12m · Hard

Screen Time
5h 18m · before bed 34m

Stress
2 / 5
```

This day-level record is the data source for insights and correlations.

---

## 14. Insights engine

Start with **deterministic rules**. No AI API.

### Example rules

```text
IF screen_time_before_bed > threshold
AND sleep duration is shorter on those days
THEN generate screen-time insight
```

```text
IF sleep duration is higher on workout days
THEN generate workout/sleep insight
```

```text
IF stress >= 4
AND sleep score is lower than the user's average
THEN generate stress/sleep insight
```

```text
IF best sleep scores cluster in a bedtime window
THEN generate bedtime insight
```

### When insights are shown

An insight is generated only if all conditions hold:

- at least **14 days** of data overall for the metrics involved;
- at least **5 days** in each compared group (e.g. days with and without high pre-bed screen time);
- the difference is meaningful (e.g. ≥ 20 minutes of sleep, or ≥ 8 score points; thresholds configurable);
- wording is "pattern in your data", never a causal claim ("you sleep less" / "your sleep tends to be shorter", not "screen time ruins your sleep").

Until then the Insights tab shows a progress indicator, not empty space.

### Storage and display

- Insights are stored as `type`, `params` (JSON), `date`; texts come from i18n keys.
- Each insight shows its basis ("based on 21 days").
- Each rule must have unit tests.

### Demo mode

A seed script / "Demo data" toggle (dev builds only) fills a test account with ~60 days of realistic data, so insights, charts and the calendar can be developed and demonstrated without waiting weeks.

---

## 15. Backend architecture

Layers:

```text
API  →  Services  →  Database (SQLAlchemy session)
```

- **API:** HTTP, authentication, validation, response formatting.
- **Services:** business logic; use the SQLAlchemy session directly (no separate Repositories layer — it adds boilerplate without benefit at this scale).
- **Analytics:** pure functions (sleep score, insight rules) with no I/O, easy to unit-test.

Services:

```text
SleepService
WorkoutService
StressService
ScreenTimeService
InsightService
UserService
```

Bot handlers call the same services.

---

## 16. Database design

Tables:

```text
users
api_tokens
sleep_sessions
workouts
stress_logs
screen_time_daily
insights
```

### users

```text
id
telegram_user_id        (bigint, unique)
language
timezone
sleep_goal_minutes
target_bedtime          (time, optional)
reminder_evening_time   (time, nullable)
reminder_morning_on     (bool)
created_at
updated_at
```

### api_tokens

```text
id
user_id
token_hash
label
created_at
last_used_at
revoked_at
```

### sleep_sessions

```text
id
user_id
started_at              (UTC)
ended_at                (UTC, nullable while open)
local_date              (date of wake-up, user's time zone)
duration_minutes        (nullable while open)
is_nap
source                  (manual | shortcut | bot | apple_health later)
created_at
updated_at
```

Constraint: at most one session per user with `ended_at IS NULL`.

### workouts

```text
id
user_id
started_at
ended_at
local_date
duration_minutes
type
intensity
created_at
```

### stress_logs

```text
id
user_id
logged_at
local_date
level                   (1–5)
category                (nullable)
```

### screen_time_daily

```text
id
user_id
date
total_minutes
before_bed_minutes
source                  (manual | shortcut)
created_at
updated_at
```

Constraint: `UNIQUE (user_id, date)`.

### insights

```text
id
user_id
type
params                  (JSON)
date
created_at
```

Soft deletion / full account deletion must remove all of the above (see Privacy).

---

## 17. Authentication

### Mini App

```text
Telegram → Mini App → initData → Backend
   → validate HMAC signature and auth_date freshness
   → create / find user
   → issue short-lived JWT
```

- Validate `initData` on the server exactly as described in the Telegram docs; reject stale `auth_date`.
- Never trust a client-provided user ID.

### Shortcuts / external clients

- Personal API token (`Authorization: Bearer <token>`), stored hashed, revocable, shown once.
- Token scope is limited to logging endpoints (sleep start/stop, screen time).

---

## 18. API endpoints

Prefix `/api/v1`. Types are generated from the OpenAPI schema.

### User

```text
GET    /me
PATCH  /me
POST   /me/api-tokens
DELETE /me/api-tokens/{id}
GET    /me/export
DELETE /me                      (delete account and all data)
```

### Sleep

```text
POST   /sleep/start
POST   /sleep/stop
POST   /sleep                   (retroactive entry)
GET    /sleep
GET    /sleep/{id}
PATCH  /sleep/{id}
DELETE /sleep/{id}
GET    /sleep/score/{date}
```

### Workout

```text
POST   /workouts/start
POST   /workouts/stop
POST   /workouts                (retroactive entry)
GET    /workouts
GET    /workouts/{id}
PATCH  /workouts/{id}
DELETE /workouts/{id}
```

### Stress

```text
POST   /stress
GET    /stress
PATCH  /stress/{id}
DELETE /stress/{id}
```

### Screen Time

```text
PUT    /screen-time/{date}      (upsert; manual form and Shortcuts)
GET    /screen-time
```

### Daily / History

```text
GET    /days/{date}             (Daily Summary)
GET    /history?range=7d|30d
```

### Insights

```text
GET    /insights
GET    /insights/progress       (how much data is collected vs. required)
```

---

## 19. Design system

Visual direction: **Dark / Emerald / Minimal / Premium**

- very dark background
- emerald accent
- large numbers
- rounded cards
- subtle gradients and glow
- minimal borders
- smooth animations
- generous whitespace
- high contrast
- no unnecessary UI

Initial colors (a starting point, to be refined):

```text
Background: #06110D
Surface:    #0D1A15
Primary:    #21D890
Text:       #F5F7F6
Muted:      #71817A
Warning:    #E5A63A
Danger:     #D94A4A
```

Also consider Telegram theme parameters (safe areas, viewport height) from the first screens.

---

## 20. UX principles

1. Logging something takes seconds.
2. The dashboard is understandable without explanation.
3. Every score and insight is explainable.
4. Historical data is visual.
5. Manual input is minimized (reminders, Shortcuts, quick buttons).
6. The app never feels like a spreadsheet.
7. Notifications are useful, not spammy, and configurable.
8. Insights are based on the user's own data and shown only when there is enough of it.
9. Do not overwhelm the user with statistics.
10. Encourage consistency rather than perfection.
11. Show "limited data" honestly instead of fake precision.

---

## 21. Privacy and data

Health-related data requires care from the first release:

- Data export and account deletion endpoints exist in the MVP.
- Privacy policy before any public beta.
- API tokens stored hashed; secrets only in environment variables.
- Data minimization: no location, no contacts, no app-level usage.
- Backups configured before real users.

---

## 22. MVP scope

### Must have

**Sleep**
- Start / Stop, retroactive entry, edit
- forgotten-Stop handling
- Sleep Score with explainable components
- sleep goal, sleep history

**Workout**
- quick timer, type, intensity
- workout history

**Stress**
- 1–5 rating, optional category, history

**Screen Time**
- manual form, upsert API, Shortcut-ready endpoint with API token

**Dashboard**
- Sleep Score hero, today's tiles, latest insight / progress hint
- Daily Summary

**History**
- 7D and 30D graphs, month calendar

**Insights**
- rule-based, with data thresholds and progress indicator
- demo mode for development

**Telegram**
- bot, Mini App launch, authentication
- evening / morning reminders with quick Start / Stop buttons

**Platform**
- localization (uk / en)
- data export and deletion
- unit tests for Sleep Score and insight rules

---

## 23. Post-MVP

**Records / PRs** (moved out of MVP — closer to a workout tracker than to a sleep product)
- exercises table (canonical names, avoid "Bench Press" vs "bench press" duplicates)
- max weight / reps / volume, fastest time, longest distance

**History**
- 90D / ALL ranges, yearly heatmap

**Integrations**
- Apple Health sleep import via Shortcuts
- screenshot parsing for Screen Time
- further wearable data if the product needs it

**Analytics**
- personal baselines, trends, anomaly detection
- more statistically robust correlations

**Notifications**
- bedtime reminder based on the user's pattern
- sleep-debt alerts, training gap reminders

**Gamification**
- streaks, achievements, weekly goals, "Progress" tab

**Social**
- weekly summary card, shareable sleep score

Not part of V1.

---

## 24. Development roadmap

Approach: build a thin **vertical slice** first (auth → record sleep → see it on Home), then widen. Do not "finalize everything" up front.

### Phase 0 — Foundations (short)
- decide core screens and data model (this document)
- Sleep Score formula draft
- design tokens

### Phase 1 — Project setup
- GitHub repository, monorepo layout
- frontend, backend, PostgreSQL, Docker Compose
- environment variables, basic CI (lint + tests)
- i18n skeleton

### Phase 2 — Telegram + vertical slice
- create bot, Mini App configuration, HTTPS tunnel for dev
- Telegram `initData` authentication, JWT, user creation
- Sleep Start / Stop end-to-end (API + UI + Home hero)

### Phase 3 — Sleep
- retroactive entry, edit, forgotten-Stop flow
- Sleep Score with cold-start handling + tests
- sleep history

### Phase 4 — Reminders
- evening / morning bot reminders with inline buttons
- reminder settings

### Phase 5 — Workout
- timer, types, intensity, history

### Phase 6 — Stress
- quick logging, history, daily aggregation

### Phase 7 — Screen Time
- manual form, upsert API
- API tokens in Settings, Shortcut templates + instructions

### Phase 8 — Dashboard & History
- Daily Summary, 7D / 30D graphs, month calendar

### Phase 9 — Insights
- rule engine with thresholds + tests
- progress indicator, demo data generator

### Phase 10 — Polish
- animations, empty / loading / error states
- performance, Telegram-specific UX

### Phase 11 — Release
- production infrastructure, monitoring
- privacy policy, backups
- beta testing

---

## 25. Definition of Done for MVP

MVP is complete when a user can:

```text
1. Open SleepGuide through Telegram
2. Press Start in the evening and Stop in the morning (in the app or via bot buttons)
3. See the Sleep Score and its breakdown
4. Start and finish a workout, see workout history
5. Log stress
6. Enter Screen Time manually or through a Shortcut
7. View history graphs and a calendar of previous days
8. See insights once enough data exists (and a progress indicator before that)
9. Have all data persisted in PostgreSQL
10. Export or delete their data
11. Use the Mini App comfortably on iPhone, in Ukrainian or English
```

---

## 26. Long-term vision

SleepGuide should grow from a tracker into a **personal sleep and habits insight tool**.

The core value is not collecting numbers. It is answering:

> **"What is affecting my sleep, and what can I change?"**

```text
   DATA (sleep · workout · stress · screen time)
                    ↓
                ANALYSIS
                    ↓
                INSIGHTS
                    ↓
            Better decisions
                    ↓
                  DATA
```
