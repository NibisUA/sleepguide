from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StressLog(Base):
    """One quick stress rating (1-5). A user can log several per day."""

    __tablename__ = "stress_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Local date (user's time zone) of `logged_at`.
    local_date: Mapped[date] = mapped_column(Date)
    level: Mapped[int] = mapped_column(Integer)
    category: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_stress_logs_user_local_date", "user_id", "local_date"),
        CheckConstraint("level BETWEEN 1 AND 5", name="level_range"),
    )
