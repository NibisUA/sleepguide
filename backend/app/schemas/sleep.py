from datetime import date, datetime

from pydantic import AwareDatetime, BaseModel, Field


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


class SleepCreateIn(BaseModel):
    """Retroactive entry ("I forgot to press Start"): both times are required."""

    started_at: AwareDatetime
    ended_at: AwareDatetime


class SleepUpdateIn(BaseModel):
    """Partial edit; omitted fields keep their value."""

    started_at: AwareDatetime | None = None
    ended_at: AwareDatetime | None = None


class SleepScoreComponentOut(BaseModel):
    model_config = {"from_attributes": True}

    key: str
    earned: float
    max: float
    detail: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class SleepScoreOut(BaseModel):
    """Sleep Score with its always-visible component breakdown."""

    model_config = {"from_attributes": True}

    date: date
    score: int
    limited_data: bool
    sleep_minutes: int
    components: list[SleepScoreComponentOut]
    algorithm_version: str


class SleepDayOut(BaseModel):
    """Aggregated calendar day for the history charts and the yearly heatmap."""

    model_config = {"from_attributes": True}

    date: date
    sleep_minutes: int
    nap_minutes: int
    bedtime: datetime | None
    wake_time: datetime | None
    score: int | None
    score_limited_data: bool
