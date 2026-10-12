import hashlib
import json
from datetime import UTC, datetime, timedelta
from statistics import pstdev

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.personal import baselines, spearman
from app.analytics.sleep_rules import local_date_of
from app.analytics.sleep_score import SCORE_ALGORITHM_VERSION, compute_sleep_score
from app.models import ScreenTimeDaily, SleepFeedback, SleepSession, StressLog, User, Workout
from app.schemas.personal import AchievementOut, CalibrationOut, GoalOut, MilestonesOut
from app.services.errors import DomainError
from app.services.sleep_service import SCORE_CONTEXT_DAYS, _to_night


async def load_nights(session, user, start, end):
    rows = (
        await session.scalars(
            select(SleepSession)
            .where(
                SleepSession.user_id == user.id,
                SleepSession.ended_at.is_not(None),
                SleepSession.is_nap.is_(False),
                SleepSession.duration_minutes > 0,
                SleepSession.local_date >= start,
                SleepSession.local_date <= end,
            )
            .order_by(SleepSession.local_date, SleepSession.started_at, SleepSession.id)
        )
    ).all()
    return [_to_night(row) for row in rows]


async def get_baselines(session: AsyncSession, user: User, now=None):
    today = local_date_of(now or datetime.now(UTC), user.timezone)
    start, end = today - timedelta(days=35), today - timedelta(days=1)
    nights = await load_nights(session, user, start, end)
    workouts = (
        await session.scalars(
            select(Workout.local_date).where(
                Workout.user_id == user.id,
                Workout.ended_at.is_not(None),
                Workout.duration_minutes > 0,
                Workout.local_date.between(start, end),
            )
        )
    ).all()
    stress = (
        await session.execute(
            select(StressLog.local_date, StressLog.level).where(
                StressLog.user_id == user.id, StressLog.local_date.between(start, end)
            )
        )
    ).all()
    screens = (
        await session.execute(
            select(ScreenTimeDaily.local_date, ScreenTimeDaily.total_minutes).where(
                ScreenTimeDaily.user_id == user.id, ScreenTimeDaily.local_date.between(start, end)
            )
        )
    ).all()
    return baselines(
        today, nights, workouts, stress, screens, user.timezone, user.reminder_pattern_on
    )


async def milestones(session: AsyncSession, user: User, now=None):
    today = local_date_of(now or datetime.now(UTC), user.timezone)
    start = today - timedelta(days=today.weekday())
    groups = {}
    for kind, model in (
        ("sleep", SleepSession),
        ("workout", Workout),
        ("stress", StressLog),
        ("screen", ScreenTimeDaily),
        ("feedback", SleepFeedback),
    ):
        query = select(model.local_date).where(model.user_id == user.id, model.local_date <= today)
        if kind in ("sleep", "workout"):
            query = query.where(model.ended_at.is_not(None), model.duration_minutes > 0)
        if kind == "sleep":
            query = query.where(model.is_nap.is_(False))
        groups[kind] = sorted(set((await session.scalars(query.distinct())).all()))
    groups["all"] = sorted(
        set().union(*(set(groups[k]) for k in ("sleep", "workout", "stress", "screen")))
    )
    awards = []
    for key, kind, target in (
        ("diary7", "all", 7),
        ("diary30", "all", 30),
        ("diary100", "all", 100),
        ("workouts10", "workout", 10),
        ("workouts50", "workout", 50),
        ("feedback7", "feedback", 7),
    ):
        dates = groups[kind]
        awards.append(
            AchievementOut(
                key=key,
                done=len(dates),
                target=target,
                earned_on=dates[target - 1] if len(dates) >= target else None,
            )
        )
    return MilestonesOut(
        week_from=start,
        week_to=start + timedelta(days=6),
        goals=[
            GoalOut(
                kind=k,
                target=getattr(user, f"weekly_{k}_days"),
                done=sum(day >= start for day in groups[k]),
            )
            for k in ("sleep", "workout", "stress", "screen")
        ],
        achievements=awards,
    )


def score_snapshot(day, nights, user):
    context = [n for n in nights if day - timedelta(days=SCORE_CONTEXT_DAYS) <= n.local_date <= day]
    score = compute_sleep_score(
        day,
        context,
        goal_minutes=user.sleep_goal_minutes,
        target_bedtime=user.target_bedtime,
        tz_name=user.timezone,
    )
    payload = [
        SCORE_ALGORITHM_VERSION,
        user.sleep_goal_minutes,
        str(user.target_bedtime),
        user.timezone,
        [
            (
                n.local_date.isoformat(),
                n.started_at.astimezone(UTC).isoformat(),
                n.ended_at.astimezone(UTC).isoformat(),
                n.minutes,
            )
            for n in context
        ],
    ]
    signature = hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()
    return score, signature


async def feedback_for_date(session, user, day):
    return await session.scalar(
        select(SleepFeedback).where(
            SleepFeedback.user_id == user.id, SleepFeedback.local_date == day
        )
    )


async def put_feedback(session, user, day, rating, now=None):
    today = local_date_of(now or datetime.now(UTC), user.timezone)
    if not today - timedelta(days=179) <= day <= today:
        raise DomainError("invalid_date", "Feedback must refer to the last 180 local days")
    nights = await load_nights(session, user, day - timedelta(days=SCORE_CONTEXT_DAYS), day)
    score, signature = score_snapshot(day, nights, user)
    if score is None:
        raise DomainError("sleep_not_found", "Feedback requires a completed main sleep")
    values = dict(
        rating=rating,
        score=score.score,
        limited_data=score.limited_data,
        algorithm_version=score.algorithm_version,
        context_signature=signature,
        components={c.key: round(c.earned / c.max, 4) for c in score.components},
    )
    await session.execute(
        insert(SleepFeedback)
        .values(user_id=user.id, local_date=day, **values)
        .on_conflict_do_update(
            constraint="uq_sleep_feedback_user_date",
            set_={**values, "updated_at": datetime.now(UTC)},
        )
    )
    await session.commit()
    return await feedback_for_date(session, user, day)


async def calibration(session, user, now=None):
    today = local_date_of(now or datetime.now(UTC), user.timezone)
    start = today - timedelta(days=179)
    rows = (
        await session.scalars(
            select(SleepFeedback)
            .where(SleepFeedback.user_id == user.id, SleepFeedback.local_date.between(start, today))
            .order_by(SleepFeedback.local_date)
        )
    ).all()
    nights = await load_nights(session, user, start - timedelta(days=SCORE_CONTEXT_DAYS), today)
    matched, stale, limited = [], 0, 0
    for row in rows:
        score, signature = score_snapshot(row.local_date, nights, user)
        if (
            score is None
            or row.context_signature != signature
            or row.algorithm_version != SCORE_ALGORITHM_VERSION
        ):
            stale += 1
        elif row.limited_data:
            limited += 1
        else:
            matched.append(row)
    ratings = [row.rating for row in matched]
    scores = [row.score for row in matched]
    raw_spread = pstdev(scores) if scores else 0
    spread = round(raw_spread, 1)
    status = (
        "collecting"
        if len(matched) < 28
        else ("needs_variation" if len(set(ratings)) < 3 or raw_spread < 5 else "ready_for_review")
    )
    usable = status == "ready_for_review"
    components = {}
    for key in ("duration", "consistency", "sleep_debt", "bedtime_timing"):
        paired = [r for r in matched if key in r.components]
        components[key] = (
            spearman([r.components[key] for r in paired], [r.rating for r in paired])
            if usable
            else None
        )
    return CalibrationOut(
        algorithm_version=SCORE_ALGORITHM_VERSION,
        from_date=start,
        to_date=today,
        required_nights=28,
        total_ratings=len(rows),
        matched_nights=len(matched),
        stale_ratings=stale,
        limited_nights=limited,
        distinct_ratings=len(set(ratings)),
        score_spread=spread,
        status=status,
        correlation=spearman(scores, ratings) if usable else None,
        component_correlations=components,
    )
