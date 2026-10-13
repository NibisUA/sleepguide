from typing import Literal

from pydantic import BaseModel, Field

CsvKind = Literal["sleep", "workout", "stress", "screen"]


class CsvImportIn(BaseModel):
    kind: CsvKind = "sleep"
    csv: str = Field(min_length=1, max_length=1_000_000)


class CsvRowOut(BaseModel):
    line: int
    date: str = ""
    summary: str = ""
    status: Literal["ready", "duplicate", "error"]
    code: str | None = None


class CsvPreviewOut(BaseModel):
    rows: list[CsvRowOut]
    ready: int
    duplicates: int
    errors: int
    imported: int = 0
    timezone: str


class CsvExportOut(BaseModel):
    filename: str
    csv: str
