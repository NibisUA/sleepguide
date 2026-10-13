from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WorkoutTemplate(Base):
    __tablename__ = "workout_templates"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80))
    type: Mapped[str] = mapped_column(String(16))
    intensity: Mapped[str] = mapped_column(String(16))
    sets: Mapped[list] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeletedEntry(Base):
    __tablename__ = "deleted_entries"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(24))
    label: Mapped[str] = mapped_column(String(160))
    payload: Mapped[dict] = mapped_column(JSONB)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    @property
    def record_id(self) -> int:
        return self.payload["row"]["id"]

    @property
    def record_key(self) -> str:
        return str(self.payload["row"]["local_date"] if self.kind == "screen" else self.record_id)
