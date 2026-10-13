from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.api_token import ApiTokenOut
from app.schemas.auth import UserOut
from app.schemas.exercise import ExerciseLogOut, ExerciseOut
from app.schemas.insight import InsightOut
from app.schemas.personal import FeedbackExportOut
from app.schemas.saved import DeletedExportOut, TemplateOut
from app.schemas.screen_time import ScreenTimeOut
from app.schemas.sleep import SleepSessionOut
from app.schemas.stress import StressLogOut
from app.schemas.workout import WorkoutOut


class UserExportOut(UserOut):
    telegram_user_id: int
    created_at: datetime
    updated_at: datetime
    last_evening_reminder_date: date | None
    last_morning_reminder_at: datetime | None


class SleepExportOut(SleepSessionOut):
    created_at: datetime
    updated_at: datetime


class WorkoutExportOut(WorkoutOut):
    created_at: datetime
    updated_at: datetime


class StressExportOut(StressLogOut):
    created_at: datetime
    updated_at: datetime


class ScreenExportOut(ScreenTimeOut):
    id: int
    created_at: datetime


class TokenExportOut(ApiTokenOut):
    revoked_at: datetime | None


class DataExportOut(BaseModel):
    schema_version: Literal["1.2"] = "1.2"
    exported_at: datetime
    user: UserExportOut
    sleep_sessions: list[SleepExportOut]
    workouts: list[WorkoutExportOut]
    stress_logs: list[StressExportOut]
    screen_time: list[ScreenExportOut]
    api_tokens: list[TokenExportOut]
    insights: list[InsightOut]
    exercises: list[ExerciseOut]
    exercise_logs: list[ExerciseLogOut]
    sleep_feedback: list[FeedbackExportOut]
    workout_templates: list[TemplateOut] = Field(default_factory=list)
    deleted_entries: list[DeletedExportOut] = Field(default_factory=list)


class DeleteMeIn(BaseModel):
    confirm: Literal[True]
