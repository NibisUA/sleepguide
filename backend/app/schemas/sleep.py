from datetime import date, datetime

from pydantic import AwareDatetime, BaseModel


class SleepSessionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    started_at: datetime
    ended_at: datetime | None
    local_date: date | None
    duration_minutes: int | None
    is_nap: bool
    source: str


class SleepStopIn(BaseModel):
    """Optional explicit wake-up time (required if the session was open > 14 h)."""

    ended_at: AwareDatetime | None = None
