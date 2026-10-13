from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import sleep_rules, sleep_score
from app.models import SleepSession, User
from app.services.diary_lock import lock_diary
from app.services.errors import DomainError

# Extra history fetched before a score/history window so consistency and cold
# start have context even when the window itself is short. The windows are bounded
# by dates, not by a row LIMIT: a LIMIT on an ascending query silently drops the
# newest sessions, i.e. the very night that is being scored.
SCORE_CONTEXT_DAYS = 120
HISTORY_CONTEXT_DAYS = SCORE_CONTEXT_DAYS


@dataclass(frozen=True)
class SleepDay:
    """One calendar day of the history view (aggregated, not a DB row)."""

    date: date
    sleep_minutes: int
    nap_minutes: int
    bedtime: datetime | None
    wake_time: datetime | None
    score: int | None
    score_limited_data: bool


async def get_open_session(session: AsyncSession, user_id: int) -> SleepSession | None:
    result = await session.execute(
        select(SleepSession).where(SleepSession.user_id == user_id, SleepSession.ended_at.is_(None))
    )
    return result.scalar_one_or_none()


async def start_sleep(
    session: AsyncSession, user: User, source: str = "manual", now: datetime | None = None
) -> SleepSession:
    """Start a session. Idempotent: if one is already open, return it (Shortcuts may fire twice)."""
    await lock_diary(session, user.id)
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
    await lock_diary(session, user.id)
    sleep = await get_open_session(session, user.id)
    if sleep is None:
        raise DomainError("no_open_session", "There is no sleep session to stop")

    if ended_at is None:
        if sleep_rules.needs_wake_confirmation(sleep.started_at, now):
            raise DomainError(
                "wake_time_required", "Session is open too long; specify wake-up time"
            )
        ended_at = now
    elif not sleep_rules.is_valid_end(sleep.started_at, ended_at, now):
        raise DomainError(
            "invalid_time", "Wake-up time must be after the start and not in the future"
        )

    if sleep_rules.is_too_long(sleep.started_at, ended_at):
        raise DomainError("too_long", "A sleep session cannot be longer than 20 hours")

    minutes = sleep_rules.duration_minutes(sleep.started_at, ended_at)
    sleep.ended_at = ended_at
    sleep.duration_minutes = minutes
    sleep.is_nap = sleep_rules.is_nap(minutes)
    sleep.local_date = sleep_rules.local_date_of(ended_at, user.timezone)
    await session.commit()
    return sleep


async def get_session(session: AsyncSession, user_id: int, sleep_id: int) -> SleepSession:
    result = await session.execute(
        select(SleepSession).where(SleepSession.id == sleep_id, SleepSession.user_id == user_id)
    )
    sleep = result.scalar_one_or_none()
    if sleep is None:
        raise DomainError("sleep_not_found", "Sleep session not found")
    return sleep


def _validate_completed(started_at: datetime, ended_at: datetime, now: datetime) -> None:
    if started_at > now + sleep_rules.MAX_FUTURE_SKEW:
        raise DomainError("invalid_time", "Sleep cannot start in the future")
    if not sleep_rules.is_valid_end(started_at, ended_at, now):
        raise DomainError(
            "invalid_time", "Wake-up time must be after the start and not in the future"
        )
    if sleep_rules.duration_minutes(started_at, ended_at) < 1:
        raise DomainError("invalid_time", "Sleep must last at least a minute")
    if sleep_rules.is_too_long(started_at, ended_at):
        raise DomainError("too_long", "A sleep session cannot be longer than 20 hours")


async def _has_overlap(
    session: AsyncSession,
    user_id: int,
    started_at: datetime,
    ended_at: datetime,
    exclude_id: int | None = None,
) -> bool:
    statement = select(SleepSession.id).where(
        SleepSession.user_id == user_id,
        SleepSession.started_at < ended_at,
        # An open session has no end yet, so it overlaps anything starting after it.
        or_(SleepSession.ended_at.is_(None), SleepSession.ended_at > started_at),
    )
    if exclude_id is not None:
        statement = statement.where(SleepSession.id != exclude_id)
    result = await session.execute(statement.limit(1))
    return result.scalar_one_or_none() is not None


async def create_session(
    session: AsyncSession,
    user: User,
    started_at: datetime,
    ended_at: datetime,
    now: datetime | None = None,
) -> SleepSession:
    """Retroactive entry: a completed sleep the user logged after the fact."""
    now = now or datetime.now(UTC)
    _validate_completed(started_at, ended_at, now)
    await lock_diary(session, user.id)
    if await _has_overlap(session, user.id, started_at, ended_at):
        raise DomainError("overlap", "This interval overlaps another sleep session")

    minutes = sleep_rules.duration_minutes(started_at, ended_at)
    sleep = SleepSession(
        user_id=user.id,
        started_at=started_at,
        ended_at=ended_at,
        duration_minutes=minutes,
        is_nap=sleep_rules.is_nap(minutes),
        local_date=sleep_rules.local_date_of(ended_at, user.timezone),
        source="retro",
    )
    session.add(sleep)
    await session.commit()
    return sleep


async def update_session(
    session: AsyncSession,
    user: User,
    sleep_id: int,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    now: datetime | None = None,
) -> SleepSession:
    """Partial edit (`None` means "keep the current value").

    Editing an open session with a new end time closes it (forgotten-Stop fix);
    a closed session is never reopened into the open state.
    """
    now = now or datetime.now(UTC)
    await lock_diary(session, user.id)
    sleep = await get_session(session, user.id, sleep_id)
    new_start = started_at or sleep.started_at
    new_end = ended_at or sleep.ended_at

    if new_end is None:
        if new_start > now + sleep_rules.MAX_FUTURE_SKEW:
            raise DomainError("invalid_time", "Sleep cannot start in the future")
        sleep.started_at = new_start
    else:
        _validate_completed(new_start, new_end, now)
        if await _has_overlap(session, user.id, new_start, new_end, exclude_id=sleep.id):
            raise DomainError("overlap", "This interval overlaps another sleep session")
        sleep.started_at = new_start
        sleep.ended_at = new_end
        minutes = sleep_rules.duration_minutes(new_start, new_end)
        sleep.duration_minutes = minutes
        sleep.is_nap = sleep_rules.is_nap(minutes)
        sleep.local_date = sleep_rules.local_date_of(new_end, user.timezone)

    await session.commit()
    return sleep


async def delete_session(session: AsyncSession, user: User, sleep_id: int) -> None:
    await lock_diary(session, user.id)
    sleep = await get_session(session, user.id, sleep_id)
    from app.services.trash_service import archive

    await archive(session, user.id, "sleep", sleep)
    await session.delete(sleep)
    await session.commit()


async def list_sessions(
    session: AsyncSession,
    user_id: int,
    limit: int = 30,
    on_date: date | None = None,
) -> list[SleepSession]:
    statement = select(SleepSession).where(SleepSession.user_id == user_id)
    if on_date is not None:
        statement = statement.where(SleepSession.local_date == on_date)
    result = await session.execute(statement.order_by(SleepSession.started_at.desc()).limit(limit))
    return list(result.scalars())


def _to_night(row: SleepSession) -> sleep_score.Night | None:
    if row.ended_at is None or row.local_date is None or row.duration_minutes is None:
        return None
    return sleep_score.Night(
        started_at=row.started_at,
        ended_at=row.ended_at,
        minutes=row.duration_minutes,
        local_date=row.local_date,
    )


async def _scored_nights(
    session: AsyncSession, user_id: int, until: date
) -> list[sleep_score.Night]:
    result = await session.execute(
        select(SleepSession)
        .where(
            SleepSession.user_id == user_id,
            SleepSession.ended_at.is_not(None),
            SleepSession.is_nap.is_(False),
            SleepSession.local_date >= until - timedelta(days=SCORE_CONTEXT_DAYS),
            SleepSession.local_date <= until,
        )
        .order_by(SleepSession.started_at)
    )
    nights: list[sleep_score.Night] = []
    for row in result.scalars():
        night = _to_night(row)
        if night is not None:
            nights.append(night)
    return nights


async def score_for_date(
    session: AsyncSession, user: User, target_date: date
) -> sleep_score.SleepScore | None:
    nights = await _scored_nights(session, user.id, target_date)
    return sleep_score.compute_sleep_score(
        target_date,
        nights,
        goal_minutes=user.sleep_goal_minutes,
        target_bedtime=user.target_bedtime,
        tz_name=user.timezone,
    )


async def history_days(
    session: AsyncSession, user: User, start_date: date, end_date: date
) -> list[SleepDay]:
    """Aggregate days in ``[start_date, end_date]`` for charts and the heatmap.

    Sessions from ``HISTORY_CONTEXT_DAYS`` before the window are fetched too so the
    per-day score has history to work with.
    """
    result = await session.execute(
        select(SleepSession)
        .where(
            SleepSession.user_id == user.id,
            SleepSession.ended_at.is_not(None),
            SleepSession.local_date >= start_date - timedelta(days=HISTORY_CONTEXT_DAYS),
            SleepSession.local_date <= end_date,
        )
        .order_by(SleepSession.started_at)
    )
    rows = list(result.scalars())

    by_date: dict[date, list[SleepSession]] = defaultdict(list)
    nights: list[sleep_score.Night] = []
    for row in rows:
        if row.local_date is not None:
            by_date[row.local_date].append(row)
        night = _to_night(row)
        if night is not None and not row.is_nap:
            nights.append(night)

    days: list[SleepDay] = []
    for offset in range((end_date - start_date).days + 1):
        day = start_date + timedelta(days=offset)
        day_rows = by_date.get(day, [])
        if not day_rows:
            days.append(
                SleepDay(
                    date=day,
                    sleep_minutes=0,
                    nap_minutes=0,
                    bedtime=None,
                    wake_time=None,
                    score=None,
                    score_limited_data=False,
                )
            )
            continue

        mains = [row for row in day_rows if not row.is_nap]
        naps = [row for row in day_rows if row.is_nap]
        main = max(mains, key=lambda row: row.duration_minutes or 0) if mains else None
        day_score = (
            sleep_score.compute_sleep_score(
                day,
                [
                    night
                    for night in nights
                    if night.local_date
                    >= date.fromordinal(max(1, day.toordinal() - SCORE_CONTEXT_DAYS))
                ],
                goal_minutes=user.sleep_goal_minutes,
                target_bedtime=user.target_bedtime,
                tz_name=user.timezone,
            )
            if main is not None
            else None
        )
        days.append(
            SleepDay(
                date=day,
                sleep_minutes=sum(row.duration_minutes or 0 for row in mains),
                nap_minutes=sum(row.duration_minutes or 0 for row in naps),
                bedtime=main.started_at if main else None,
                wake_time=main.ended_at if main else None,
                score=day_score.score if day_score else None,
                score_limited_data=bool(day_score and day_score.limited_data),
            )
        )
    return days
