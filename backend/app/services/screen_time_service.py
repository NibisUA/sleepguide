from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import screen_time_rules, sleep_rules
from app.models import ScreenTimeDaily, User
from app.services.diary_lock import lock_diary
from app.services.errors import DomainError


async def _find(session: AsyncSession, user_id: int, day: date) -> ScreenTimeDaily | None:
    result = await session.execute(
        select(ScreenTimeDaily).where(
            ScreenTimeDaily.user_id == user_id, ScreenTimeDaily.local_date == day
        )
    )
    return result.scalar_one_or_none()


async def upsert(
    session: AsyncSession,
    user: User,
    day: date,
    total_minutes: int,
    before_bed_minutes: int | None,
    source: str = "manual",
    now: datetime | None = None,
    categories: dict[str, int | None] | None = None,
) -> ScreenTimeDaily:
    """Create or replace the record of a day (idempotent: a Shortcut may send it twice)."""
    await lock_diary(session, user.id)
    now = now or datetime.now(UTC)
    today = sleep_rules.local_date_of(now, user.timezone)
    if not screen_time_rules.is_date_in_range(day, today):
        raise DomainError("invalid_date", "The date must be within the last year and not in the future")
    if not screen_time_rules.is_valid_usage(total_minutes, before_bed_minutes):
        raise DomainError(
            "invalid_screen_time", "Pre-bed usage cannot exceed 2 hours or the daily total"
        )

    def apply(row: ScreenTimeDaily) -> None:
        # Older Shortcuts send only a total: retain breakdown unless explicitly cleared.
        merged = {key: getattr(row, key) for key in screen_time_rules.SCREEN_CATEGORIES}
        merged.update(categories or {})
        if not screen_time_rules.valid_categories(total_minutes, merged):
            raise DomainError("invalid_screen_categories", "Category minutes cannot exceed the total")
        for key, value in merged.items():
            setattr(row, key, value)
        row.total_minutes = total_minutes
        row.before_bed_minutes = before_bed_minutes
        row.source = source
        row.updated_at = now

    row = await _find(session, user.id, day)
    if row is not None:
        apply(row)
        await session.commit()
        return row

    row = ScreenTimeDaily(user_id=user.id, local_date=day, created_at=now)
    apply(row)
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:  # a concurrent request created the day first: update that record
        await session.rollback()
        row = await _find(session, user.id, day)
        if row is None:
            raise
        apply(row)
        await session.commit()
    return row


async def list_range(
    session: AsyncSession, user_id: int, start_date: date, end_date: date
) -> list[ScreenTimeDaily]:
    result = await session.execute(
        select(ScreenTimeDaily)
        .where(
            ScreenTimeDaily.user_id == user_id,
            ScreenTimeDaily.local_date >= start_date,
            ScreenTimeDaily.local_date <= end_date,
        )
        .order_by(ScreenTimeDaily.local_date)
    )
    return list(result.scalars())


async def delete_day(session: AsyncSession, user: User, day: date) -> None:
    await lock_diary(session, user.id)
    row = await _find(session, user.id, day)
    if row is None:
        raise DomainError("screen_time_not_found", "No record for this day")
    await session.delete(row)
    await session.commit()
