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


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
