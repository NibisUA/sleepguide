from datetime import date
from typing import Literal

from pydantic import BaseModel


class StreakOut(BaseModel):
    kind: Literal["all", "sleep", "workout", "stress", "screen"]
    current: int
    longest: int
    total_days: int
    last_date: date | None
    counted_today: bool


class ProgressOut(BaseModel):
    today: date
    timezone: str
    streaks: list[StreakOut]
