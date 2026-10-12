from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import sleep_rules, stress_rules
from app.models import StressLog, User
from app.schemas.stress import StressDayOut
from app.services.errors import DomainError


def _validate_time(logged_at: datetime, now: datetime) -> None:
    if logged_at > now + sleep_rules.MAX_FUTURE_SKEW:
        raise DomainError("invalid_time", "A rating cannot be in the future")


async def get_log(session: AsyncSession, user_id: int, log_id: int) -> StressLog:
    result = await session.execute(
        select(StressLog).where(StressLog.id == log_id, StressLog.user_id == user_id)
    )
    log = result.scalar_one_or_none()
    if log is None:
        raise DomainError("stress_not_found", "Stress record not found")
    return log


async def create_log(
    session: AsyncSession,
    user: User,
    level: int,
    category: str | None = None,
    logged_at: datetime | None = None,
    now: datetime | None = None,
) -> StressLog:
    now = now or datetime.now(UTC)
    logged_at = logged_at or now
    _validate_time(logged_at, now)
    log = StressLog(
        user_id=user.id,
        logged_at=logged_at,
        local_date=sleep_rules.local_date_of(logged_at, user.timezone),
        level=level,
        category=category,
    )
    session.add(log)
    await session.commit()
    return log


async def update_log(
    session: AsyncSession,
    user: User,
    log_id: int,
    changes: dict[str, Any],
    now: datetime | None = None,
) -> StressLog:
    """Apply a partial edit. `changes` holds only the fields the client sent."""
    log = await get_log(session, user.id, log_id)
    if changes.get("level") is not None:
        log.level = changes["level"]
    if "category" in changes:  # null clears the category
        log.category = changes["category"]
    if changes.get("logged_at") is not None:
        _validate_time(changes["logged_at"], now or datetime.now(UTC))
        log.logged_at = changes["logged_at"]
        log.local_date = sleep_rules.local_date_of(log.logged_at, user.timezone)
    await session.commit()
    return log


async def delete_log(session: AsyncSession, user: User, log_id: int) -> None:
    log = await get_log(session, user.id, log_id)
    await session.delete(log)
    await session.commit()


async def list_logs(
    session: AsyncSession,
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
) -> list[StressLog]:
    statement = select(StressLog).where(StressLog.user_id == user_id)
    if start_date is not None:
        statement = statement.where(StressLog.local_date >= start_date)
    if end_date is not None:
        statement = statement.where(StressLog.local_date <= end_date)
    result = await session.execute(statement.order_by(StressLog.logged_at.desc()).limit(limit))
    return list(result.scalars())


async def history_days(
    session: AsyncSession, user: User, start_date: date, end_date: date
) -> list[StressDayOut]:
    """Per-day count, average and maximum for ``[start_date, end_date]`` (every day is included)."""
    result = await session.execute(
        select(StressLog).where(
            StressLog.user_id == user.id,
            StressLog.local_date >= start_date,
            StressLog.local_date <= end_date,
        )
    )
    levels: dict[date, list[int]] = defaultdict(list)
    for row in result.scalars():
        levels[row.local_date].append(row.level)

    days: list[StressDayOut] = []
    for offset in range((end_date - start_date).days + 1):
        day = start_date + timedelta(days=offset)
        values = levels.get(day, [])
        days.append(
            StressDayOut(
                date=day,
                count=len(values),
                average=stress_rules.day_average(values),
                max=stress_rules.day_max(values),
                level_sum=sum(values),
            )
        )
    return days
