from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SleepFeedback(Base):
    __tablename__ = "sleep_feedback"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    local_date: Mapped[date] = mapped_column(Date)
    rating: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    limited_data: Mapped[bool]
    algorithm_version: Mapped[str] = mapped_column(String(16))
    context_signature: Mapped[str] = mapped_column(String(64))
    components: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    __table_args__ = (
        UniqueConstraint("user_id", "local_date", name="uq_sleep_feedback_user_date"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating"),
        CheckConstraint("score BETWEEN 0 AND 100", name="score"),
    )
