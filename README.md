# SleepGuide

A Telegram Mini App for tracking sleep, workouts, stress, and screen time,
with personal progress views and rule-based insights.

Built by [NibisUA](https://github.com/NibisUA) as a full-stack application using
**React, TypeScript, FastAPI, PostgreSQL, and aiogram**.

## What the app does

- Records sleep sessions and explains the components of a sleep score.
- Tracks workouts, exercise sets, personal records, and logging streaks.
- Captures stress ratings and screen time, including local screenshot OCR.
- Shows daily summaries, history charts, and personal insights.
- Sends configurable Telegram reminders and supports iOS Shortcuts.
- Provides CSV/JSON data transfer, saved workout templates, and recoverable deletion.
- Tracks user-defined deadline plans with weighted schedules, progress history, and local text/screenshot import.
- Supports Ukrainian and English interfaces (the deadline tracker is Ukrainian).

Deadline tracker setup and import rules: [docs/DEADLINE_TRACKER.md](docs/DEADLINE_TRACKER.md).

## Architecture

| Area | Implementation |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS, TanStack Query, i18next |
| Backend | FastAPI, Pydantic, async SQLAlchemy, Alembic |
| Storage | PostgreSQL with versioned database migrations |
| Telegram | aiogram bot, signed Telegram authentication, webhook integration |
| Quality | Backend and frontend test suites, type checks, linting, CI, secret scanning |
| Deployment | Docker Compose and Caddy; documented backup and restore procedures |

The bot and API share the backend process. The frontend communicates with the
versioned `/api/v1` API. Personal API tokens support restricted Shortcuts actions;
the browser application uses session authentication.

## Run locally

Prerequisites: Docker with Compose and Node.js 22 or later. A Telegram bot token
is optional for browser-only development.

```bash
git clone https://github.com/NibisUA/sleepguide.git
cd sleepguide
cp backend/.env.example backend/.env
docker compose up --build
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open **http://localhost:5173**. The API documentation is available at
**http://localhost:8000/docs**. For browser development, use `ENV=dev` and
`DEV_LOGIN_ENABLED=true` in the local backend environment file.

Local database credentials in `docker-compose.yml` are development defaults.
Production uses separately configured secrets; see the release guide.

## Run checks

From `backend/`, using Python 3.12 or later and a virtual environment:

```bash
python -m pip install -e ".[dev]"
ruff check .
python -m pytest -q
```

PostgreSQL integration tests need the test database configuration used by CI.
From `frontend/`:

```bash
npm ci
npm run typecheck
npm test
npm run build
```

The checked-in workflow runs the backend and frontend checks. Test commands are
provided for reproducibility; deployment and device validation are tracked in
the project documentation.

## Configuration and security

Real credentials belong in local `.env` files or a deployment secret store.
Sanitized `.env.example` files document the expected settings. Environment files,
private keys, database backups, logs, and generated exports are excluded from Git.

See [SECURITY.md](SECURITY.md) for credential handling and secret scanning.
The sleep score uses transparent, versioned rules; empirical calibration remains
an ongoing part of the project.

## Project documentation

- [Development guide and Telegram setup](docs/DEVELOPMENT_GUIDE.md)
- [Release and deployment](docs/RELEASE.md)
- [Implementation status and known limitations](docs/STATUS.md)
- [Product scope](docs/product.md)
- [CSV transfer and workout logging](docs/CSV_SHORTCUTS_WORKOUTS.md)
- [Workout templates and recoverable deletion](docs/TEMPLATES_AND_UNDO.md)
- [Personal progress and local OCR](docs/PERSONAL_PROGRESS.md)
- [iOS Shortcuts setup](shortcuts/README.md)
