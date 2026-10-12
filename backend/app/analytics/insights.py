"""Deterministic associations, never causal claims. No I/O.

A night ending on D is paired with lifestyle records from D-1. Missing screen
time / stress is unknown, never zero. Bedtimes use fixed local clock hours.
Only distinct completed, non-nap sleep days count.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from statistics import mean
from typing import Literal

MIN_DAYS = 14
MIN_GROUP_DAYS = 5
MIN_SLEEP_DIFFERENCE = 20
MIN_SCORE_DIFFERENCE = 8
HIGH_SCREEN_MINUTES = 60
HIGH_STRESS = 4
WINDOW_DAYS = 90
ALGORITHM_VERSION = "1.0"
InsightType = Literal["screen_sleep", "workout_sleep", "stress_score", "bedtime_score"]


@dataclass(frozen=True)
class Observation:
    date: date  # wake-up date
    sleep_minutes: int
    score: int
    bedtime_hour: int
    before_bed_minutes: int | None = None
    workout_minutes: int = 0  # no completed workout logged
    stress_average: float | None = None


@dataclass(frozen=True)
class Finding:
    type: InsightType
    message_key: str
    params: dict[str, str | int | float]
    sample_days: int
    period_start: date
    period_end: date


def _comparison(
    kind: InsightType,
    key: str,
    group: list[Observation],
    reference: list[Observation],
    metric: str,
    threshold: int,
    extra: dict[str, str | int | float] | None = None,
) -> Finding | None:
    if min(len(group), len(reference)) < MIN_GROUP_DAYS:
        return None
    group_mean = mean(getattr(day, metric) for day in group)
    reference_mean = mean(getattr(day, metric) for day in reference)
    difference = group_mean - reference_mean
    # 19.9 minutes must not pass a 20-minute gate by rounding.
    if abs(difference) < threshold:
        return None
    used = group + reference
    return Finding(
        type=kind,
        message_key=f"insights.messages.{key}_{'higher' if difference > 0 else 'lower'}",
        params={
            "difference": round(abs(difference), 1),
            "group_days": len(group),
            "reference_days": len(reference),
            "group_average": round(group_mean, 1),
            "reference_average": round(reference_mean, 1),
            **(extra or {}),
        },
        sample_days=len(used),
        period_start=min(day.date for day in used),
        period_end=max(day.date for day in used),
    )


def analyze(days: Sequence[Observation]) -> list[Finding]:
    days = sorted({day.date: day for day in days}.values(), key=lambda day: day.date)
    if len(days) < MIN_DAYS:
        return []
    screen = [day for day in days if day.before_bed_minutes is not None]
    stress = [day for day in days if day.stress_average is not None]
    candidates = [
        _comparison(
            "screen_sleep",
            "screen",
            [day for day in screen if day.before_bed_minutes >= HIGH_SCREEN_MINUTES],
            [day for day in screen if day.before_bed_minutes < HIGH_SCREEN_MINUTES],
            "sleep_minutes",
            MIN_SLEEP_DIFFERENCE,
            {"threshold": HIGH_SCREEN_MINUTES},
        ),
        _comparison(
            "workout_sleep",
            "workout",
            [day for day in days if day.workout_minutes > 0],
            [day for day in days if day.workout_minutes == 0],
            "sleep_minutes",
            MIN_SLEEP_DIFFERENCE,
        ),
        _comparison(
            "stress_score",
            "stress",
            [day for day in stress if day.stress_average >= HIGH_STRESS],
            [day for day in stress if day.stress_average < HIGH_STRESS],
            "score",
            MIN_SCORE_DIFFERENCE,
            {"threshold": HIGH_STRESS},
        ),
    ]
    findings = [finding for finding in candidates if finding is not None]
    # Fixed bins avoid selecting a custom window that happens to fit the data.
    bins = {hour: [day for day in days if day.bedtime_hour == hour] for hour in range(24)}
    eligible = [hour for hour, group in bins.items() if len(group) >= MIN_GROUP_DAYS]
    if eligible:
        best = min(eligible, key=lambda hour: (-mean(day.score for day in bins[hour]), hour))
        finding = _comparison(
            "bedtime_score",
            "bedtime",
            bins[best],
            [day for day in days if day.bedtime_hour != best],
            "score",
            MIN_SCORE_DIFFERENCE,
            {"from": f"{best:02d}:00", "to": f"{(best + 1) % 24:02d}:00"},
        )
        if finding and finding.message_key.endswith("_higher"):
            findings.append(finding)
    return findings
