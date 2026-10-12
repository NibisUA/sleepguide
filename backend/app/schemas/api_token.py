from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class ApiTokenCreateIn(BaseModel):
    model_config = {"str_strip_whitespace": True}

    label: Annotated[str, Field(min_length=1, max_length=40)]


class ApiTokenOut(BaseModel):
    """A token as listed in Settings: never contains the secret."""

    model_config = {"from_attributes": True}

    id: int
    label: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None


class ApiTokenCreatedOut(ApiTokenOut):
    """Returned once, right after creation: the only time the secret is visible."""

    token: str
