from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.screen_time import ScreenTimeOut
from app.schemas.sleep import SleepSessionOut
from app.schemas.stress import StressLogOut
from app.schemas.workout import WorkoutOut

HistoryRange = Literal["7d", "30d", "90d", "all"]
HistoryKind = Literal["sleep", "workout", "stress", "screen"]


class SleepHistorySummary(BaseModel):
    days: int
    average_minutes: float | None
    average_score: float | None
    nap_minutes: int


class WorkoutHistorySummary(BaseModel):
    count: int
    minutes: int


class StressHistorySummary(BaseModel):
    count: int
    average: float | None
    peak: int | None


class ScreenHistorySummary(BaseModel):
    days: int
    average_total: float | None
    average_before_bed: float | None


class HistoryPointOut(BaseModel):
    date: date
    end_date: date
    sleep_minutes: float | None
    score: float | None
    workout_count: int
    workout_minutes: int
    stress_count: int
    stress_average: float | None
    stress_max: int | None
    screen_total: float | None
    screen_before_bed: float | None


class HistoryOverviewOut(BaseModel):
    range: HistoryRange
    from_date: date
    to_date: date
    days: int
    bucket_days: int
    has_data: bool
    sleep: SleepHistorySummary
    workout: WorkoutHistorySummary
    stress: StressHistorySummary
    screen: ScreenHistorySummary
    points: list[HistoryPointOut]


class HistoryEntriesOut(BaseModel):
    kind: HistoryKind
    sleep_sessions: list[SleepSessionOut] = Field(default_factory=list)
    workouts: list[WorkoutOut] = Field(default_factory=list)
    stress_logs: list[StressLogOut] = Field(default_factory=list)
    screen_time: list[ScreenTimeOut] = Field(default_factory=list)
    next_cursor: str | None
