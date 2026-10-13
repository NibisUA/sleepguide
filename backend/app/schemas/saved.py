from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.exercise import ExerciseLogCreateIn, clean_name
from app.schemas.workout import WorkoutIntensity, WorkoutType


class TemplateCreateIn(BaseModel):
    model_config = {"extra": "forbid"}
    name: str
    workout_id: int = Field(gt=0)
    _name = field_validator("name")(clean_name)


class TemplateOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    name: str
    type: WorkoutType
    intensity: WorkoutIntensity
    sets: list[ExerciseLogCreateIn]
    created_at: datetime


class DeletedOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    kind: str
    record_id: int
    record_key: str
    label: str
    deleted_at: datetime
    expires_at: datetime


class DeletedExportOut(DeletedOut):
    payload: dict
