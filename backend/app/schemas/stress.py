from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field

StressCategory = Literal[
    "university", "work", "relationships", "money", "sleep", "training", "personal", "other"
]
StressLevel = Annotated[int, Field(ge=1, le=5)]


class StressLogOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    logged_at: datetime
    local_date: date
    level: int
    category: StressCategory | None


class StressCreateIn(BaseModel):
    level: StressLevel
    category: StressCategory | None = None
    logged_at: AwareDatetime | None = None  # default: now


class StressUpdateIn(BaseModel):
    """Partial edit; omitted fields keep their value, `category: null` clears the category."""

    level: StressLevel | None = None
    category: StressCategory | None = None
    logged_at: AwareDatetime | None = None


class StressDayOut(BaseModel):
    """One calendar day for the history chart (days without ratings are included)."""

    date: date
    count: int
    average: float | None
    max: int | None
    level_sum: int
