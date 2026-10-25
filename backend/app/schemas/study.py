import re
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class StudyItemIn(BaseModel):
    label: str = Field(min_length=1, max_length=32)
    title: str = Field(default="", max_length=160)
    group: str = Field(default="", max_length=80)
    weight: int = Field(default=1, ge=1, le=100, strict=True)
    scheduled_date: date | None = None

    @field_validator("label")
    @classmethod
    def canonical_label(cls, value):
        value = value.strip().upper().replace("Н", "N").replace("№", "")
        if not re.fullmatch(r"(?:N\d+\.)?\d+", value) or int(value.split(".")[-1]) < 1:
            raise ValueError("Номер: 1 або N1.1. Підпункти без N не є окремими питаннями")
        return value


class StudyPlanIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    deadline: date
    start_date: date | None = None
    total: int = Field(ge=1, le=1000, strict=True)
    reserve_days: int = Field(default=0, ge=0, le=365, strict=True)
    daily_capacity: int | None = Field(default=None, ge=1, le=10000, strict=True)
    items: list[StudyItemIn] | None = Field(default=None, min_length=1, max_length=1000)
    preserve_schedule: bool = False
    expected_version: int | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Вкажи назву")
        return value

    @model_validator(mode="after")
    def valid_items(self):
        if self.items is not None:
            labels = [row.label for row in self.items]
            if len(labels) != len(set(labels)):
                raise ValueError("Повторні номери питань")
            if len(labels) != self.total:
                raise ValueError("Кількість не збігається зі списком")
        return self


class StudyItemOut(StudyItemIn):
    done_at: datetime | None = None


class StudyPlanOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    name: str
    deadline: date
    start_date: date
    reserve_days: int
    daily_capacity: int | None
    items: list[StudyItemOut]
    version: int
    created_at: datetime


class StudyVersionIn(BaseModel):
    expected_version: int


class StudyCheckIn(StudyVersionIn):
    done: bool


class StudyMoveIn(StudyVersionIn):
    date: date


class StudyEventOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    plan_id: int
    kind: str
    detail: dict
    created_at: datetime


class StudyReplanIn(StudyVersionIn):
    assignments: dict[str, date | None]


class StudyParseIn(BaseModel):
    text: str = Field(min_length=1, max_length=60000)
    year: int | None = Field(default=None, ge=2000, le=2100)
