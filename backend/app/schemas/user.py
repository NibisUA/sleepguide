from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class UserUpdate(BaseModel):
    language: Annotated[str, Field(pattern="^(uk|en)$")] | None = None
    timezone: str | None = None
    sleep_goal_minutes: Annotated[int, Field(ge=240, le=720)] | None = None

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
