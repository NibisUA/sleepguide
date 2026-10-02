from pydantic import BaseModel


class TelegramLoginIn(BaseModel):
    init_data: str


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    language: str
    timezone: str
    sleep_goal_minutes: int


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
