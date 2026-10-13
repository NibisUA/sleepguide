from datetime import time

from pydantic import BaseModel


class TelegramLoginIn(BaseModel):
    init_data: str


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    language: str
    timezone: str
    sleep_goal_minutes: int
    target_bedtime: time | None = None
    reminder_evening_time: time | None = None
    reminder_morning_on: bool = True
    reminder_sound_on: bool = True
    reminder_pattern_on: bool = False
    weekly_sleep_days: int = 5
    weekly_workout_days: int = 3
    weekly_stress_days: int = 3
    weekly_screen_days: int = 3


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
