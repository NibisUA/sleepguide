"""Pure Sleep Score computation (no I/O).

See docs/product.md §8:

    Duration        40   — vs. the user's sleep goal
    Consistency     30   — regularity of bedtime and wake-up over recent days
    Sleep debt      20   — accumulated deficit over the last 7 days
    Bedtime timing  10   — not too late relative to the user's target

Cold start: with fewer than ``COLD_START_MIN_DAYS`` days of sleep data the
consistency and sleep-debt components are omitted and the score is computed
from the remaining components with their weights renormalized (still /100).

The score is computed on the fly from sessions; nothing is stored.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from statistics import pstdev
from zoneinfo import ZoneInfo

SCORE_ALGORITHM_VERSION = "1.0"

WEIGHT_DURATION = 40.0
WEIGHT_CONSISTENCY = 30.0
WEIGHT_SLEEP_DEBT = 20.0
WEIGHT_BEDTIME_TIMING = 10.0

COLD_START_MIN_DAYS = 7

CONSISTENCY_WINDOW_NIGHTS = 14
CONSISTENCY_MIN_NIGHTS = 4
# No penalty below 20 min of spread between nights; zero points at 2 h.
CONSISTENCY_FULL_SPREAD_MINUTES = 20.0
CONSISTENCY_ZERO_SPREAD_MINUTES = 120.0

DEBT_WINDOW_DAYS = 7
# One full night of accumulated deficit (8 h) zeroes the sleep-debt component.
DEBT_ZERO_SCORE_MINUTES = 8 * 60

BEDTIME_GRACE_MINUTES = 30.0
BEDTIME_ZERO_SCORE_MINUTES = 120.0
DEFAULT_TARGET_BEDTIME = time(23, 0)


@dataclass(frozen=True)
class Night:
    """A completed main (non-nap) sleep; ``local_date`` is the wake-up date."""

    started_at: datetime
    ended_at: datetime
    minutes: int
    local_date: date


@dataclass(frozen=True)
class ComponentScore:
    key: str
    earned: float
    max: float
    detail: dict[str, str | int | float | bool | None] = field(default_factory=dict)


@dataclass(frozen=True)
class SleepScore:
    date: date
    score: int
    limited_data: bool
    sleep_minutes: int
    components: tuple[ComponentScore, ...]
    algorithm_version: str = SCORE_ALGORITHM_VERSION


def compute_sleep_score(
    target_date: date,
    nights: Sequence[Night],
    *,
    goal_minutes: int = 480,
    target_bedtime: time | None = None,
    tz_name: str = "UTC",
) -> SleepScore | None:
    """Score the sleep that ended on ``target_date``.

    ``nights`` must contain completed main sleeps only (naps are excluded by the
    caller); nights after ``target_date`` are ignored. Returns ``None`` when
    there is no sleep for ``target_date``.
    """
    scored = [n for n in nights if n.local_date <= target_date]
    day_nights = [n for n in scored if n.local_date == target_date]
    if not day_nights:
        return None

    sleep_minutes = sum(n.minutes for n in day_nights)
    known_days = {n.local_date for n in scored}
    limited = len(known_days) < COLD_START_MIN_DAYS

    components = [_duration_score(sleep_minutes, goal_minutes)]
    components.append(_bedtime_timing_score(_latest(day_nights), target_bedtime, tz_name))

    if not limited:
        consistency = _consistency_score(scored, tz_name)
        debt = _sleep_debt_score(scored, target_date, goal_minutes)
        if consistency is not None:
            components.append(consistency)
        if debt is not None:
            components.append(debt)
        # A component can be missing even with enough days of data; that is
        # still "limited data" for the explainability label.
        limited = consistency is None or debt is None

    earned = sum(c.earned for c in components)
    maximal = sum(c.max for c in components)
    score = round(100 * earned / maximal) if maximal else 0
    return SleepScore(
        date=target_date,
        score=int(score),
        limited_data=limited,
        sleep_minutes=sleep_minutes,
        components=tuple(components),
    )


def _latest(nights: Sequence[Night]) -> Night:
    return max(nights, key=lambda n: n.ended_at)


def _ratio(value: float, full_at: float, zero_at: float) -> float:
    """1.0 while ``value <= full_at``, 0.0 from ``zero_at`` on, linear between."""
    if value <= full_at:
        return 1.0
    if value >= zero_at:
        return 0.0
    return (zero_at - value) / (zero_at - full_at)


def _duration_score(minutes: int, goal_minutes: int) -> ComponentScore:
    goal = max(goal_minutes, 1)
    earned = WEIGHT_DURATION * min(minutes / goal, 1.0)
    return ComponentScore(
        key="duration",
        earned=round(earned, 1),
        max=WEIGHT_DURATION,
        detail={"minutes": minutes, "goal_minutes": goal_minutes},
    )


def _consistency_score(nights: Sequence[Night], tz_name: str) -> ComponentScore | None:
    recent = sorted(nights, key=lambda n: n.local_date)[-CONSISTENCY_WINDOW_NIGHTS:]
    if len(recent) < CONSISTENCY_MIN_NIGHTS:
        return None
    bedtime_spread = pstdev([_bedtime_index(n.started_at, tz_name) for n in recent])
    wake_spread = pstdev([_minutes_of_day(n.ended_at, tz_name) for n in recent])
    spread = (bedtime_spread + wake_spread) / 2
    earned = WEIGHT_CONSISTENCY * _ratio(
        spread, CONSISTENCY_FULL_SPREAD_MINUTES, CONSISTENCY_ZERO_SPREAD_MINUTES
    )
    return ComponentScore(
        key="consistency",
        earned=round(earned, 1),
        max=WEIGHT_CONSISTENCY,
        detail={
            "bedtime_spread_minutes": round(bedtime_spread),
            "wake_spread_minutes": round(wake_spread),
            "nights": len(recent),
        },
    )


def _sleep_debt_score(
    nights: Sequence[Night], target_date: date, goal_minutes: int
) -> ComponentScore | None:
    window_start = target_date - timedelta(days=DEBT_WINDOW_DAYS - 1)
    # Days without any record are not counted: missing data is not a debt.
    minutes_by_day: dict[date, int] = {}
    for night in nights:
        if window_start <= night.local_date <= target_date:
            minutes_by_day[night.local_date] = max(
                minutes_by_day.get(night.local_date, 0), night.minutes
            )
    if not minutes_by_day:
        return None
    deficit = sum(max(0, goal_minutes - minutes) for minutes in minutes_by_day.values())
    earned = WEIGHT_SLEEP_DEBT * _ratio(deficit, 0.0, float(DEBT_ZERO_SCORE_MINUTES))
    return ComponentScore(
        key="sleep_debt",
        earned=round(earned, 1),
        max=WEIGHT_SLEEP_DEBT,
        detail={
            "deficit_minutes": deficit,
            "days_counted": len(minutes_by_day),
            "window_days": DEBT_WINDOW_DAYS,
        },
    )


def _bedtime_timing_score(
    night: Night, target_bedtime: time | None, tz_name: str
) -> ComponentScore:
    target = target_bedtime or DEFAULT_TARGET_BEDTIME
    late = max(0, _bedtime_index(night.started_at, tz_name) - _time_index(target))
    # Going to bed earlier than the target is never penalized.
    earned = WEIGHT_BEDTIME_TIMING * _ratio(late, BEDTIME_GRACE_MINUTES, BEDTIME_ZERO_SCORE_MINUTES)
    return ComponentScore(
        key="bedtime_timing",
        earned=round(earned, 1),
        max=WEIGHT_BEDTIME_TIMING,
        detail={
            "bedtime": _clock(night.started_at, tz_name),
            "target_bedtime": target.strftime("%H:%M"),
            "late_minutes": late,
            "used_default_target": target_bedtime is None,
        },
    )


def _local(moment: datetime, tz_name: str) -> datetime:
    return moment.astimezone(ZoneInfo(tz_name))


def _bedtime_index(moment: datetime, tz_name: str) -> int:
    """Minutes since noon: keeps an evening bedtime and an after-midnight one close."""
    local = _local(moment, tz_name)
    return (local.hour * 60 + local.minute - 720) % 1440


def _minutes_of_day(moment: datetime, tz_name: str) -> int:
    local = _local(moment, tz_name)
    return local.hour * 60 + local.minute


def _time_index(value: time) -> int:
    return (value.hour * 60 + value.minute - 720) % 1440


def _clock(moment: datetime, tz_name: str) -> str:
    local = _local(moment, tz_name)
    return f"{local.hour:02d}:{local.minute:02d}"
