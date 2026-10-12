from datetime import date

from pydantic import BaseModel

from app.schemas.screen_time import ScreenTimeOut
from app.schemas.sleep import SleepScoreOut, SleepSessionOut
from app.schemas.stress import StressDayOut, StressLogOut
from app.schemas.workout import WorkoutOut


class DaySummaryOut(BaseModel):
    """Everything logged for one local day, across all four areas."""

    date: date
    # Sleep that ended on this day (the night) and every finished sleep session of the day.
    sleep_score: SleepScoreOut | None
    sleep_sessions: list[SleepSessionOut]
    workouts: list[WorkoutOut]  # finished workouts that started on this day
    workout_minutes: int
    stress: StressDayOut  # count / average / max (count = 0 when nothing was logged)
    stress_logs: list[StressLogOut]
    screen_time: ScreenTimeOut | None
