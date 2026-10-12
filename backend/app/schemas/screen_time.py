from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field


class ScreenTimeIn(BaseModel):
    total_minutes: Annotated[int, Field(ge=0, le=1440)]
    # Phone use in the ~2 hours before bed; must not exceed the total (checked by the service).
    before_bed_minutes: Annotated[int, Field(ge=0, le=120)] | None = None


class ScreenTimeOut(BaseModel):
    model_config = {"from_attributes": True}

    local_date: date
    total_minutes: int
    before_bed_minutes: int | None
    source: str
    updated_at: datetime
