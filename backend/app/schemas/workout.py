from datetime import date, datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel

WorkoutType = Literal["gym", "home", "running", "football", "walking", "other"]
WorkoutIntensity = Literal["easy", "moderate", "hard", "very_hard"]


class WorkoutOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    started_at: datetime
    ended_at: datetime | None
    local_date: date
    duration_minutes: int | None
    type: WorkoutType
    intensity: WorkoutIntensity
    source: str


class WorkoutStartIn(BaseModel):
    type: WorkoutType = "gym"
    intensity: WorkoutIntensity = "moderate"


class WorkoutStopIn(BaseModel):
    """Finishing a workout; the intensity (and type) can still be corrected here."""

    ended_at: AwareDatetime | None = None  # required if the workout has run for over 6 hours
    type: WorkoutType | None = None
    intensity: WorkoutIntensity | None = None


class WorkoutCreateIn(BaseModel):
    """Retroactive entry: all fields are required."""

    started_at: AwareDatetime
    ended_at: AwareDatetime
    type: WorkoutType
    intensity: WorkoutIntensity


class WorkoutUpdateIn(BaseModel):
    """Partial edit; omitted fields keep their value."""

    started_at: AwareDatetime | None = None
    ended_at: AwareDatetime | None = None
    type: WorkoutType | None = None
    intensity: WorkoutIntensity | None = None


class WorkoutDayOut(BaseModel):
    """One calendar day for the history chart (days without workouts are included)."""

    date: date
    count: int
    minutes: int
