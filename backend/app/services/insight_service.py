from collections import defaultdict
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import insights, sleep_rules
from app.models import Insight, ScreenTimeDaily, StressLog, User, Workout
from app.schemas.insight import InsightsProgressOut
from app.services import sleep_service


async def observations(
    session: AsyncSession, user: User, now: datetime | None = None
) -> list[insights.Observation]:
    today = sleep_rules.local_date_of(now or datetime.now(UTC), user.timezone)
    start = today - timedelta(days=insights.WINDOW_DAYS - 1)
    sleep = await sleep_service.history_days(session, user, start, today)
    activity_start, activity_end = start - timedelta(days=1), today - timedelta(days=1)
    workouts = (
        await session.execute(
            select(Workout).where(
                Workout.user_id == user.id,
                Workout.local_date >= activity_start,
                Workout.local_date <= activity_end,
                Workout.ended_at.is_not(None),
            )
        )
    ).scalars()
    stress = (
        await session.execute(
            select(StressLog).where(
                StressLog.user_id == user.id,
                StressLog.local_date >= activity_start,
                StressLog.local_date <= activity_end,
            )
        )
    ).scalars()
    screen = (
        await session.execute(
            select(ScreenTimeDaily).where(
                ScreenTimeDaily.user_id == user.id,
                ScreenTimeDaily.local_date >= activity_start,
                ScreenTimeDaily.local_date <= activity_end,
            )
        )
    ).scalars()
    workout_minutes: dict = defaultdict(int)
    stress_levels: dict = defaultdict(list)
    for row in workouts:
        workout_minutes[row.local_date] += row.duration_minutes or 0
    for row in stress:
        stress_levels[row.local_date].append(row.level)
    screen_by_day = {row.local_date: row.before_bed_minutes for row in screen}
    result = []
    for day in sleep:
        if day.sleep_minutes <= 0 or day.score is None or day.bedtime is None:
            continue
        previous = day.date - timedelta(days=1)
        levels = stress_levels.get(previous, [])
        result.append(
            insights.Observation(
                date=day.date,
                sleep_minutes=day.sleep_minutes,
                score=day.score,
                bedtime_hour=day.bedtime.astimezone(ZoneInfo(user.timezone)).hour,
                before_bed_minutes=screen_by_day.get(previous),
                workout_minutes=workout_minutes.get(previous, 0),
                stress_average=sum(levels) / len(levels) if levels else None,
            )
        )
    return result


async def progress(session: AsyncSession, user: User) -> InsightsProgressOut:
    days = await observations(session, user)
    return InsightsProgressOut(
        days=len(days),
        required_days=insights.MIN_DAYS,
        minimum_group_days=insights.MIN_GROUP_DAYS,
        window_days=insights.WINDOW_DAYS,
        ready=len(days) >= insights.MIN_DAYS,
        paired_screen_days=sum(day.before_bed_minutes is not None for day in days),
        paired_stress_days=sum(day.stress_average is not None for day in days),
    )


async def refresh(session: AsyncSession, user: User) -> list[Insight]:
    # Serialize refreshes for this user; concurrent Home/Insights reads are safe.
    await session.execute(select(User.id).where(User.id == user.id).with_for_update())
    findings = insights.analyze(await observations(session, user))
    existing = list(
        (await session.execute(select(Insight).where(Insight.user_id == user.id))).scalars()
    )
    by_type = {row.type: row for row in existing}
    active = {finding.type for finding in findings}
    for row in existing:
        if row.type not in active:
            await session.delete(row)
    result = []
    for finding in findings:
        values = {
            "message_key": finding.message_key,
            "params": finding.params,
            "sample_days": finding.sample_days,
            "period_start": finding.period_start,
            "period_end": finding.period_end,
            "algorithm_version": insights.ALGORITHM_VERSION,
        }
        row = by_type.get(finding.type)
        if row is None:
            row = Insight(
                user_id=user.id, type=finding.type, **values, generated_at=datetime.now(UTC)
            )
            session.add(row)
        elif any(getattr(row, key) != value for key, value in values.items()):
            for key, value in values.items():
                setattr(row, key, value)
            row.generated_at = datetime.now(UTC)
        result.append(row)
    await session.commit()
    return sorted(result, key=lambda row: (row.generated_at, row.type), reverse=True)
