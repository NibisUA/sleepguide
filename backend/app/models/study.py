from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StudyPlan(Base):
    __tablename__ = "study_plans"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    deadline: Mapped[date] = mapped_column(Date)
    start_date: Mapped[date] = mapped_column(Date)
    reserve_days: Mapped[int] = mapped_column(Integer, default=0)
    daily_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    items: Mapped[list] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("id", "user_id", name="uq_study_plans_id_user_id"),)


class StudyEvent(Base):
    __tablename__ = "study_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(24))
    detail: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        ForeignKeyConstraint(
            ["plan_id", "user_id"], ["study_plans.id", "study_plans.user_id"], ondelete="CASCADE"
        ),
    )
