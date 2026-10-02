from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import sleep_rules
from app.models import SleepSession, User
from app.services.errors import DomainError


async def get_open_session(session: AsyncSession, user_id: int) -> SleepSession | None:
    result = await session.execute(
        select(SleepSession).where(
            SleepSession.user_id == user_id, SleepSession.ended_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def start_sleep(
    session: AsyncSession, user: User, source: str = "manual", now: datetime | None = None
) -> SleepSession:
    """Start a session. Idempotent: if one is already open, return it (Shortcuts may fire twice)."""
    existing = await get_open_session(session, user.id)
    if existing:
        return existing
    sleep = SleepSession(user_id=user.id, started_at=now or datetime.now(UTC), source=source)
    session.add(sleep)
    try:
        await session.commit()
    except IntegrityError:  # race with a concurrent start
        await session.rollback()
        existing = await get_open_session(session, user.id)
        if existing is None:
            raise
        return existing
    return sleep


async def stop_sleep(
    session: AsyncSession,
    user: User,
    ended_at: datetime | None = None,
    now: datetime | None = None,
) -> SleepSession:
    """Close the open session.

    If the session has been open for more than 14 hours and no explicit wake-up time is given,
    raise `wake_time_required`: the client must ask the user when they actually woke up.
    """
    now = now or datetime.now(UTC)
    sleep = await get_open_session(session, user.id)
    if sleep is None:
        raise DomainError("no_open_session", "There is no sleep session to stop")

    if ended_at is None:
        if sleep_rules.needs_wake_confirmation(sleep.started_at, now):
            raise DomainError("wake_time_required", "Session is open too long; specify wake-up time")
        ended_at = now
    elif not sleep_rules.is_valid_end(sleep.started_at, ended_at, now):
        raise DomainError("invalid_time", "Wake-up time must be after the start and not in the future")

    minutes = sleep_rules.duration_minutes(sleep.started_at, ended_at)
    sleep.ended_at = ended_at
    sleep.duration_minutes = minutes
    sleep.is_nap = sleep_rules.is_nap(minutes)
    sleep.local_date = sleep_rules.local_date_of(ended_at, user.timezone)
    await session.commit()
    return sleep


async def list_sessions(session: AsyncSession, user_id: int, limit: int = 30) -> list[SleepSession]:
    result = await session.execute(
        select(SleepSession)
        .where(SleepSession.user_id == user_id)
        .order_by(SleepSession.started_at.desc())
        .limit(limit)
    )
    return list(result.scalars())
