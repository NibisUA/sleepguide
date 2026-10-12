"""Bounded chart buckets and exact summaries. Missing values are never zeros."""

from datetime import date, timedelta
from math import ceil

from app.schemas.history import HistoryOverviewOut, HistoryPointOut, HistoryRange

MAX_POINTS = 90


def mean(total, count):
    return total / count if count else None


def build_overview(
    start: date,
    end: date,
    range_name: HistoryRange,
    has_data: bool,
    sleeps: list,
    workouts: list,
    stress: list,
    screens: list,
) -> HistoryOverviewOut:
    span = (end - start).days + 1
    bucket_days = max(1, ceil(span / MAX_POINTS))
    bins = [{} for _ in range(ceil(span / bucket_days))]
    totals = {}

    def add(day, **values):
        bucket = bins[(day - start).days // bucket_days]
        for key, value in values.items():
            if key == "stress_peak":
                bucket[key] = max(bucket.get(key, 0), value)
                totals[key] = max(totals.get(key, 0), value)
            else:
                bucket[key] = bucket.get(key, 0) + value
                totals[key] = totals.get(key, 0) + value

    for day, minutes, naps, score in sleeps:
        values = dict(sleep_minutes=minutes, sleep_days=int(minutes > 0), nap_minutes=naps)
        if score is not None:
            values.update(score_sum=score, score_days=1)
        add(day, **values)
    for day, count, minutes in workouts:
        add(day, workout_count=count, workout_minutes=minutes)
    for day, count, level_sum, peak in stress:
        add(day, stress_count=count, stress_sum=level_sum, stress_peak=peak)
    for day, total, before in screens:
        values = dict(screen_days=1, screen_total=total)
        if before is not None:
            values.update(screen_before=before, screen_before_days=1)
        add(day, **values)

    def average(values, numerator, denominator):
        return mean(values.get(numerator, 0), values.get(denominator, 0))

    points = []
    for index, values in enumerate(bins):
        day = start + timedelta(days=index * bucket_days)
        points.append(
            HistoryPointOut(
                date=day,
                end_date=min(day + timedelta(days=bucket_days - 1), end),
                sleep_minutes=average(values, "sleep_minutes", "sleep_days"),
                score=average(values, "score_sum", "score_days"),
                workout_count=values.get("workout_count", 0),
                workout_minutes=values.get("workout_minutes", 0),
                stress_count=values.get("stress_count", 0),
                stress_average=average(values, "stress_sum", "stress_count"),
                stress_max=values.get("stress_peak"),
                screen_total=average(values, "screen_total", "screen_days"),
                screen_before_bed=average(values, "screen_before", "screen_before_days"),
            )
        )
    return HistoryOverviewOut(
        range=range_name,
        from_date=start,
        to_date=end,
        days=span,
        bucket_days=bucket_days,
        has_data=has_data,
        points=points,
        sleep=dict(
            days=totals.get("sleep_days", 0),
            nap_minutes=totals.get("nap_minutes", 0),
            average_minutes=average(totals, "sleep_minutes", "sleep_days"),
            average_score=average(totals, "score_sum", "score_days"),
        ),
        workout=dict(
            count=totals.get("workout_count", 0), minutes=totals.get("workout_minutes", 0)
        ),
        stress=dict(
            count=totals.get("stress_count", 0),
            peak=totals.get("stress_peak"),
            average=average(totals, "stress_sum", "stress_count"),
        ),
        screen=dict(
            days=totals.get("screen_days", 0),
            average_total=average(totals, "screen_total", "screen_days"),
            average_before_bed=average(totals, "screen_before", "screen_before_days"),
        ),
    )
