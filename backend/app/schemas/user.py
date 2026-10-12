from datetime import time
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class UserUpdate(BaseModel):
    language: Annotated[str, Field(pattern="^(uk|en)$")] | None = None
    timezone: str | None = None
    sleep_goal_minutes: Annotated[int, Field(ge=240, le=720)] | None = None
    target_bedtime: time | None = None  # null clears the target (the default is used)
    reminder_evening_time: time | None = None  # null turns the evening reminder off
    reminder_morning_on: bool | None = None
    reminder_pattern_on: bool | None = None
    weekly_sleep_days: Annotated[int, Field(ge=0, le=7, strict=True)] | None = None
    weekly_workout_days: Annotated[int, Field(ge=0, le=7, strict=True)] | None = None
    weekly_stress_days: Annotated[int, Field(ge=0, le=7, strict=True)] | None = None
    weekly_screen_days: Annotated[int, Field(ge=0, le=7, strict=True)] | None = None

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("unknown time zone") from None
        return value
