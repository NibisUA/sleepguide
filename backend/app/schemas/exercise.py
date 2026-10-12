import unicodedata
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ExerciseKind = Literal["strength", "cardio"]


def clean_name(value: str) -> str:
    value = " ".join(unicodedata.normalize("NFKC", value).split())
    if not value or len(value) > 80 or any(unicodedata.category(c).startswith("C") for c in value):
        raise ValueError("Exercise name must be 1–80 printable characters")
    return value


class ExerciseCreateIn(BaseModel):
    model_config = {"extra": "forbid"}
    name: str
    kind: ExerciseKind
    _name = field_validator("name")(clean_name)


class ExerciseRenameIn(BaseModel):
    model_config = {"extra": "forbid"}
    name: str
    _name = field_validator("name")(clean_name)


class ExerciseOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    name: str
    kind: ExerciseKind
    created_at: datetime
    updated_at: datetime


class ExerciseMetricsIn(BaseModel):
    model_config = {"extra": "forbid"}
    weight_kg: Decimal | None = Field(None, ge=0, le=2000, max_digits=6, decimal_places=2)
    reps: int | None = Field(None, ge=1, le=1000, strict=True)
    distance_m: int | None = Field(None, ge=1, le=1000000, strict=True)
    duration_seconds: int | None = Field(None, ge=1, le=21600, strict=True)

    @model_validator(mode="after")
    def valid_shape(self):
        strength = self.weight_kg is not None and self.reps is not None
        cardio = self.distance_m is not None
        if strength and not cardio and self.duration_seconds is None:
            return self
        if cardio and self.weight_kg is None and self.reps is None:
            return self
        raise ValueError("Supply one strength set or one distance effort")


class ExerciseLogCreateIn(ExerciseMetricsIn):
    exercise_id: int = Field(gt=0)


class ExerciseLogOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    workout_id: int
    exercise_id: int
    weight_kg: float | None
    reps: int | None
    distance_m: int | None
    duration_seconds: int | None
    created_at: datetime
    updated_at: datetime


class RecordOut(BaseModel):
    metric: Literal["weight", "reps", "set_volume", "distance", "time"]
    value: float
    log_id: int
    workout_id: int
    date: date
    weight_kg: float | None
    reps: int | None
    distance_m: int | None
    duration_seconds: int | None


class ExerciseRecordsOut(BaseModel):
    exercise: ExerciseOut
    records: list[RecordOut]
