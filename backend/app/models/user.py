from datetime import datetime, time

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    language: Mapped[str] = mapped_column(String(8), default="uk")
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Kyiv")
    sleep_goal_minutes: Mapped[int] = mapped_column(Integer, default=480)
    target_bedtime: Mapped[time | None] = mapped_column(Time, nullable=True)
    reminder_evening_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    reminder_morning_on: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
