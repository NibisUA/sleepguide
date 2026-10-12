"""ENV=dev only; seed an EMPTY dev-login account without deleting existing data.

Run from backend: python -m app.seed.demo
"""

import asyncio
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.api.auth import DEV_TELEGRAM_USER_ID
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models import Exercise, ScreenTimeDaily, SleepSession, StressLog, User, Workout
from app.seed.exercises import seed_exercises


def require_dev() -> None:
    if get_settings().env != "dev":
        raise RuntimeError("Demo data is allowed only with ENV=dev")


def demo_rows(user_id: int, timezone: str, now: datetime | None = None) -> list:
    """60 completed nights; alternate contrasting groups for all four rules."""
    zone = ZoneInfo(timezone)
    today = (now or datetime.now(UTC)).astimezone(zone).date()
    rows = []
    for offset in range(60, 0, -1):
        wake_day = today - timedelta(days=offset)
        activity_day = wake_day - timedelta(days=1)
        good = offset % 2 == 0
        # Poor nights begin AFTER midnight: the activity day remains D-1.
        start_day = activity_day if good else wake_day
        start = datetime.combine(start_day, time(22, 30) if good else time(0, 30), zone)
        minutes = (500 if good else 390) + offset % 5 * 3
        end = start.astimezone(UTC) + timedelta(minutes=minutes)
        rows.append(
            SleepSession(
                user_id=user_id,
                started_at=start.astimezone(UTC),
                ended_at=end,
                local_date=wake_day,
                duration_minutes=minutes,
                is_nap=False,
                source="retro",
            )
        )
        logged = datetime.combine(activity_day, time(17), zone).astimezone(UTC)
        if good:
            rows.append(
                Workout(
                    user_id=user_id,
                    started_at=logged,
                    ended_at=logged + timedelta(minutes=45),
                    local_date=activity_day,
                    duration_minutes=45,
                    type="walking",
                    intensity="moderate",
                    source="retro",
                )
            )
        rows.extend(
            [
                StressLog(
                    user_id=user_id,
                    logged_at=logged,
                    local_date=activity_day,
                    level=2 if good else 4,
                    category="work",
                ),
                ScreenTimeDaily(
                    user_id=user_id,
                    local_date=activity_day,
                    total_minutes=180 if good else 360,
                    before_bed_minutes=20 if good else 90,
                    source="manual",
                ),
            ]
        )
    return rows


async def seed() -> None:
    require_dev()  # must run before even opening a connection
    async with SessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_user_id == DEV_TELEGRAM_USER_ID).with_for_update()
            )
        ).scalar_one_or_none()
        if user is None:
            user = User(
                telegram_user_id=DEV_TELEGRAM_USER_ID,
                language="uk",
                timezone="Europe/Kyiv",
                sleep_goal_minutes=480,
            )
            session.add(user)
            await session.flush()
        for model in (SleepSession, Workout, StressLog, ScreenTimeDaily, Exercise):
            found = (
                await session.execute(select(model.id).where(model.user_id == user.id).limit(1))
            ).scalar_one_or_none()
            if found is not None:
                raise RuntimeError("Dev account has records; demo seed refuses to overwrite them")
        rows = demo_rows(user.id, user.timezone)
        session.add_all(rows)
        await session.flush()
        await seed_exercises(session, user.id, [row for row in rows if isinstance(row, Workout)])
        await session.commit()
    print("Created 60 demo nights for the dev-login account")


if __name__ == "__main__":
    require_dev()
    asyncio.run(seed())
