import base64
import json
from collections import defaultdict, deque
from datetime import UTC, date, datetime, timedelta

from pydantic import AwareDatetime, BaseModel, Field, ValidationError
from sqlalchemy import func, select, tuple_, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import sleep_rules, sleep_score
from app.analytics.history import build_overview
from app.models import ScreenTimeDaily, SleepSession, StressLog, User, Workout
from app.schemas.history import HistoryEntriesOut, HistoryKind, HistoryOverviewOut, HistoryRange
from app.services.errors import DomainError
from app.services.sleep_service import SCORE_CONTEXT_DAYS, _to_night


def completed_dates(user_id):
    return [
        select(SleepSession.local_date.label("day")).where(
            SleepSession.user_id == user_id, SleepSession.ended_at.is_not(None)
        ),
        select(Workout.local_date.label("day")).where(
            Workout.user_id == user_id, Workout.ended_at.is_not(None)
        ),
        select(StressLog.local_date.label("day")).where(StressLog.user_id == user_id),
        select(ScreenTimeDaily.local_date.label("day")).where(ScreenTimeDaily.user_id == user_id),
    ]


async def overview(
    session: AsyncSession, user: User, range_name: HistoryRange, now: datetime | None = None
) -> HistoryOverviewOut:
    today = sleep_rules.local_date_of(now or datetime.now(UTC), user.timezone)
    dates = union_all(*completed_dates(user.id)).subquery()
    earliest = await session.scalar(select(func.min(dates.c.day)).where(dates.c.day <= today))
    start = (
        (earliest or today)
        if range_name == "all"
        else today - timedelta(days=int(range_name[:-1]) - 1)
    )
    context = date.fromordinal(max(1, start.toordinal() - SCORE_CONTEXT_DAYS))
    sleep_rows = list(
        (
            await session.scalars(
                select(SleepSession)
                .where(
                    SleepSession.user_id == user.id,
                    SleepSession.ended_at.is_not(None),
                    SleepSession.local_date >= context,
                    SleepSession.local_date <= today,
                )
                .order_by(SleepSession.local_date, SleepSession.started_at, SleepSession.id)
            )
        ).all()
    )
    by_date = defaultdict(list)
    for row in sleep_rows:
        by_date[row.local_date].append(row)
    recent = deque()
    sleeps = []
    for day, rows in sorted(by_date.items()):
        cutoff = date.fromordinal(max(1, day.toordinal() - SCORE_CONTEXT_DAYS))
        while recent and recent[0].local_date < cutoff:
            recent.popleft()
        for row in rows:
            night = _to_night(row)
            if night is not None and not row.is_nap:
                recent.append(night)
        if day < start:
            continue
        minutes = sum(row.duration_minutes or 0 for row in rows if not row.is_nap)
        naps = sum(row.duration_minutes or 0 for row in rows if row.is_nap)
        score = (
            sleep_score.compute_sleep_score(
                day,
                recent,
                goal_minutes=user.sleep_goal_minutes,
                target_bedtime=user.target_bedtime,
                tz_name=user.timezone,
            )
            if minutes
            else None
        )
        sleeps.append((day, minutes, naps, score.score if score else None))
    workouts = (
        await session.execute(
            select(Workout.local_date, func.count(), func.sum(Workout.duration_minutes))
            .where(
                Workout.user_id == user.id,
                Workout.ended_at.is_not(None),
                Workout.duration_minutes > 0,
                Workout.local_date >= start,
                Workout.local_date <= today,
            )
            .group_by(Workout.local_date)
        )
    ).all()
    stress = (
        await session.execute(
            select(
                StressLog.local_date,
                func.count(),
                func.sum(StressLog.level),
                func.max(StressLog.level),
            )
            .where(
                StressLog.user_id == user.id,
                StressLog.local_date >= start,
                StressLog.local_date <= today,
            )
            .group_by(StressLog.local_date)
        )
    ).all()
    screens = (
        await session.execute(
            select(
                ScreenTimeDaily.local_date,
                ScreenTimeDaily.total_minutes,
                ScreenTimeDaily.before_bed_minutes,
            ).where(
                ScreenTimeDaily.user_id == user.id,
                ScreenTimeDaily.local_date >= start,
                ScreenTimeDaily.local_date <= today,
            )
        )
    ).all()
    return build_overview(
        start,
        today,
        range_name,
        bool(sleeps or workouts or stress or screens),
        sleeps,
        workouts,
        stress,
        screens,
    )


class EntryCursor(BaseModel):
    model_config = {"extra": "forbid"}
    day: date
    stamp: AwareDatetime
    id: int = Field(gt=0, le=2**63 - 1, strict=True)


def decode_cursor(raw: str, start: date, end: date) -> EntryCursor:
    try:
        value = base64.b64decode(raw + "=" * (-len(raw) % 4), altchars=b"-_", validate=True)
        cursor = EntryCursor.model_validate_json(value)
        if not start <= cursor.day <= end:
            raise ValueError("Cursor date outside range")
        return cursor
    except (ValueError, ValidationError):
        raise DomainError("invalid_cursor", "Invalid history cursor") from None


def encode_cursor(row, stamp) -> str:
    value = json.dumps(
        {"day": row.local_date.isoformat(), "stamp": stamp.isoformat(), "id": row.id},
        separators=(",", ":"),
    )
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


async def entries(
    session: AsyncSession,
    user: User,
    kind: HistoryKind,
    start: date,
    end: date,
    cursor: str | None,
    limit: int,
) -> HistoryEntriesOut:
    today = sleep_rules.local_date_of(datetime.now(UTC), user.timezone)
    if start > end or end > today:
        raise DomainError("invalid_range", "History dates must be ordered and not in the future")
    model, timestamp, field = {
        "sleep": (SleepSession, SleepSession.started_at, "sleep_sessions"),
        "workout": (Workout, Workout.started_at, "workouts"),
        "stress": (StressLog, StressLog.logged_at, "stress_logs"),
        "screen": (ScreenTimeDaily, ScreenTimeDaily.updated_at, "screen_time"),
    }[kind]
    statement = select(model).where(
        model.user_id == user.id, model.local_date >= start, model.local_date <= end
    )
    if kind in ("sleep", "workout"):
        statement = statement.where(model.ended_at.is_not(None))
    if cursor:
        key = decode_cursor(cursor, start, end)
        statement = statement.where(
            tuple_(model.local_date, timestamp, model.id) < tuple_(key.day, key.stamp, key.id)
        )
    rows = list(
        (
            await session.scalars(
                statement.order_by(
                    model.local_date.desc(), timestamp.desc(), model.id.desc()
                ).limit(limit + 1)
            )
        ).all()
    )
    visible = rows[:limit]
    last = visible[-1] if visible else None
    next_cursor = encode_cursor(last, getattr(last, timestamp.key)) if len(rows) > limit else None
    return HistoryEntriesOut(kind=kind, next_cursor=next_cursor, **{field: visible})
