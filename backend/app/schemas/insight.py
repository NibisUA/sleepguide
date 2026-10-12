from datetime import date, datetime

from pydantic import BaseModel

from app.analytics.insights import InsightType


class InsightOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    type: InsightType
    message_key: str
    params: dict[str, str | int | float]
    sample_days: int
    period_start: date
    period_end: date
    algorithm_version: str
    generated_at: datetime


class InsightsProgressOut(BaseModel):
    days: int
    required_days: int
    minimum_group_days: int
    window_days: int
    ready: bool
    paired_screen_days: int
    paired_stress_days: int
