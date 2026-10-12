from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas.day import DaySummaryOut
from app.schemas.screen_time import ScreenTimeOut
from app.schemas.sleep import SleepScoreOut, SleepSessionOut
from app.schemas.stress import StressLogOut
from app.schemas.workout import WorkoutOut
from app.services import (
    screen_time_service,
    sleep_service,
    stress_service,
    workout_service,
)


async def build_summary(session: AsyncSession, user: User, day: date) -> DaySummaryOut:
    """Aggregate the day from the per-module services (six small queries)."""
    score = await sleep_service.score_for_date(session, user, day)
    sessions = await sleep_service.list_sessions(session, user.id, limit=20, on_date=day)
    workouts = [
        workout
        for workout in await workout_service.list_workouts(session, user.id, day, day, limit=50)
        if workout.ended_at is not None  # a workout that is still running is not a result yet
    ]
    stress_days = await stress_service.history_days(session, user, day, day)
    stress_logs = await stress_service.list_logs(session, user.id, day, day, limit=100)
    screen_rows = await screen_time_service.list_range(session, user.id, day, day)

    return DaySummaryOut(
        date=day,
        sleep_score=SleepScoreOut.model_validate(score) if score is not None else None,
        sleep_sessions=[
            SleepSessionOut.model_validate(row) for row in sessions if row.ended_at is not None
        ],
        workouts=[WorkoutOut.model_validate(workout) for workout in workouts],
        workout_minutes=sum(workout.duration_minutes or 0 for workout in workouts),
        stress=stress_days[0],
        stress_logs=[StressLogOut.model_validate(log) for log in stress_logs],
        screen_time=ScreenTimeOut.model_validate(screen_rows[0]) if screen_rows else None,
    )
