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
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ScreenTimeDaily(Base):
    """Phone screen time for one local day (entered manually or sent by an iOS Shortcut)."""

    __tablename__ = "screen_time_daily"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    local_date: Mapped[date] = mapped_column(Date)
    total_minutes: Mapped[int] = mapped_column(Integer)
    # Phone use in the ~2 hours before going to bed (the user's estimate); optional.
    before_bed_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="manual")  # manual | shortcut
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "local_date", name="uq_screen_time_user_local_date"),
        CheckConstraint("total_minutes BETWEEN 0 AND 1440", name="total_range"),
        CheckConstraint(
            "before_bed_minutes IS NULL OR "
            "(before_bed_minutes BETWEEN 0 AND 120 AND before_bed_minutes <= total_minutes)",
            name="before_bed_valid",
        ),
    )
