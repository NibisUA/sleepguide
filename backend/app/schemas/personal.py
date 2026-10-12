from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class BaselineMetricOut(BaseModel):
    key: Literal["sleep", "screen", "stress", "workout"]
    recent: float | None
    baseline: float | None
    delta: float | None
    recent_days: int
    baseline_days: int
    ready: bool


class PatternOut(BaseModel):
    time: str | None
    bedtime: str | None
    nights: int
    spread_minutes: int | None
    enabled: bool


class BaselinesOut(BaseModel):
    recent_from: date
    recent_to: date
    baseline_from: date
    baseline_to: date
    metrics: list[BaselineMetricOut]
    reminder: PatternOut


class GoalOut(BaseModel):
    kind: Literal["sleep", "workout", "stress", "screen"]
    target: int
    done: int


class AchievementOut(BaseModel):
    key: str
    done: int
    target: int
    earned_on: date | None


class MilestonesOut(BaseModel):
    week_from: date
    week_to: date
    goals: list[GoalOut]
    achievements: list[AchievementOut]


class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5, strict=True)


class FeedbackOut(BaseModel):
    model_config = {"from_attributes": True}
    local_date: date
    rating: int
    score: int
    limited_data: bool
    algorithm_version: str
    updated_at: datetime


class FeedbackExportOut(FeedbackOut):
    id: int
    context_signature: str
    components: dict
    created_at: datetime


class CalibrationOut(BaseModel):
    algorithm_version: str
    from_date: date
    to_date: date
    required_nights: int
    total_ratings: int
    matched_nights: int
    stale_ratings: int
    limited_nights: int
    distinct_ratings: int
    score_spread: float
    status: Literal["collecting", "needs_variation", "ready_for_review"]
    correlation: float | None
    component_correlations: dict[str, float | None]
    weights_changed: bool = False
