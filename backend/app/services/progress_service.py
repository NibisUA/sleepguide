from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.sleep_rules import local_date_of
from app.analytics.streaks import count_streaks
from app.models import ScreenTimeDaily, SleepSession, StressLog, User, Workout
from app.schemas.progress import ProgressOut, StreakOut


async def progress(session: AsyncSession, user: User, now: datetime | None = None) -> ProgressOut:
    today = local_date_of(now or datetime.now(UTC), user.timezone)
    groups = {}
    for kind, statement in (
        (
            "sleep",
            select(SleepSession.local_date).where(
                SleepSession.user_id == user.id,
                SleepSession.ended_at.is_not(None),
                SleepSession.is_nap.is_(False),
                SleepSession.duration_minutes > 0,
            ),
        ),
        (
            "workout",
            select(Workout.local_date).where(
                Workout.user_id == user.id,
                Workout.ended_at.is_not(None),
                Workout.duration_minutes > 0,
            ),
        ),
        ("stress", select(StressLog.local_date).where(StressLog.user_id == user.id)),
        ("screen", select(ScreenTimeDaily.local_date).where(ScreenTimeDaily.user_id == user.id)),
    ):
        groups[kind] = set((await session.execute(statement.distinct())).scalars())
    groups = {"all": set().union(*groups.values()), **groups}
    return ProgressOut(
        today=today,
        timezone=user.timezone,
        streaks=[
            StreakOut(kind=kind, **count_streaks(days, today)) for kind, days in groups.items()
        ],
    )
