from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(80))
    name_key: Mapped[str] = mapped_column(String(240))
    kind: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    __table_args__ = (
        UniqueConstraint("user_id", "name_key", name="uq_exercises_user_name_key"),
        UniqueConstraint("id", "user_id", name="uq_exercises_id_user_id"),
        CheckConstraint("kind IN ('strength', 'cardio')", name="kind"),
    )


class ExerciseLog(Base):
    """One strength set or one distance effort inside a completed workout."""

    __tablename__ = "exercise_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    workout_id: Mapped[int] = mapped_column(BigInteger)
    exercise_id: Mapped[int] = mapped_column(BigInteger)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["workout_id", "user_id"], ["workouts.id", "workouts.user_id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["exercise_id", "user_id"], ["exercises.id", "exercises.user_id"], ondelete="CASCADE"
        ),
        CheckConstraint(
            "(weight_kg IS NOT NULL AND weight_kg BETWEEN 0 AND 2000 AND reps BETWEEN 1 AND 1000 "
            "AND reps IS NOT NULL AND distance_m IS NULL AND duration_seconds IS NULL) OR "
            "(weight_kg IS NULL AND reps IS NULL AND distance_m BETWEEN 1 AND 1000000 "
            "AND distance_m IS NOT NULL AND (duration_seconds IS NULL OR "
            "duration_seconds BETWEEN 1 AND 21600))",
            name="metrics",
        ),
        Index("ix_exercise_logs_user_exercise", "user_id", "exercise_id"),
        Index("ix_exercise_logs_user_workout", "user_id", "workout_id"),
    )
