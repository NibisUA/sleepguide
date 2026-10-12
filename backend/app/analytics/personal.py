"""Descriptive personal comparisons; missing observations never become zeros."""

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, median, pstdev
from zoneinfo import ZoneInfo

from app.analytics.sleep_score import Night
from app.schemas.personal import BaselineMetricOut, BaselinesOut, PatternOut


def bedtime_pattern(nights: list[Night], today: date, timezone: str, enabled=False) -> PatternOut:
    # One main sleep per wake-up day; daytime sleeps cannot drive a night reminder.
    by_day = {
        n.local_date: n
        for n in sorted(nights, key=lambda n: n.ended_at)
        if today - timedelta(days=28) <= n.local_date < today
    }
    values = []
    for night in by_day.values():
        local = night.started_at.astimezone(ZoneInfo(timezone))
        minute = local.hour * 60 + local.minute
        if minute >= 18 * 60 or minute < 6 * 60:
            values.append((minute - 720) % 1440)
    spread = round(pstdev(values)) if values else None
    valid = len(values) >= 14 and spread is not None and spread <= 60
    minute = round(median(values) + 720) % 1440 if valid else None

    def clock(value):
        return f"{value // 60:02d}:{value % 60:02d}" if value is not None else None

    return PatternOut(
        time=clock((minute - 30) % 1440 if minute is not None else None),
        bedtime=clock(minute),
        nights=len(values),
        spread_minutes=spread,
        enabled=enabled,
    )


def baselines(today, nights, workouts, stress, screens, timezone, enabled=False):
    recent_start = today - timedelta(days=7)
    baseline_start = today - timedelta(days=35)
    values = {kind: defaultdict(list) for kind in ("sleep", "workout", "stress", "screen")}
    for night in nights:
        values["sleep"][night.local_date].append(night.minutes)
    for day in workouts:
        values["workout"][day].append(1)
    for day, level in stress:
        values["stress"][day].append(level)
    for day, minutes in screens:
        values["screen"][day].append(minutes)
    known = set().union(*(set(group) for group in values.values()))
    metrics = []
    for kind, days in values.items():

        def period(start, end):
            picked = {day: nums for day, nums in days.items() if start <= day <= end}
            if kind == "workout":
                # Count distinct workout days. Scale baseline 28 days to one week.
                coverage = sum(start <= day <= end for day in known)
                return (len(picked) * 7 / ((end - start).days + 1) if coverage else None), coverage
            # Stress daily means give each observed day equal weight.
            averages = [(sum(nums) if kind == "sleep" else mean(nums)) for nums in picked.values()]
            return (mean(averages) if averages else None), len(picked)

        recent, rd = period(recent_start, today - timedelta(days=1))
        baseline, bd = period(baseline_start, recent_start - timedelta(days=1))
        ready = rd >= 3 and bd >= 14 and recent is not None and baseline is not None
        metrics.append(
            BaselineMetricOut(
                key=kind,
                recent=round(recent, 1) if recent is not None else None,
                baseline=round(baseline, 1) if baseline is not None else None,
                delta=round(recent - baseline, 1) if ready else None,
                recent_days=rd,
                baseline_days=bd,
                ready=ready,
            )
        )
    return BaselinesOut(
        recent_from=recent_start,
        recent_to=today - timedelta(days=1),
        baseline_from=baseline_start,
        baseline_to=recent_start - timedelta(days=1),
        metrics=metrics,
        reminder=bedtime_pattern(nights, today, timezone, enabled),
    )


def spearman(left, right):
    if len(left) < 3 or len(set(left)) < 2 or len(set(right)) < 2:
        return None

    def ranks(values):
        positions = defaultdict(list)
        for i, value in enumerate(sorted(values), 1):
            positions[value].append(i)
        ranked = {value: mean(indices) for value, indices in positions.items()}
        return [ranked[value] for value in values]

    a, b = ranks(left), ranks(right)
    am, bm = mean(a), mean(b)
    denominator = (sum((v - am) ** 2 for v in a) * sum((v - bm) ** 2 for v in b)) ** 0.5
    return round(sum((x - am) * (y - bm) for x, y in zip(a, b)) / denominator, 3)
