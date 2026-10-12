from datetime import date, timedelta

import pytest

from app.analytics.streaks import count_streaks
from app.schemas.exercise import ExerciseCreateIn, ExerciseMetricsIn

TODAY = date(2026, 10, 12)


@pytest.mark.parametrize(
    "offsets,current,longest,total",
    [
        ([], 0, 0, 0),
        ([0], 1, 1, 1),
        ([-1], 1, 1, 1),
        ([-2], 0, 1, 1),
        ([-3, -2, -1], 3, 3, 3),
        ([-3, -2, -1, 0], 4, 4, 4),
        ([-10, -9, -8, -7, -1, 0], 2, 4, 6),
        ([1, 2], 0, 0, 0),
        ([-1, 0, 1], 2, 2, 2),
    ],
)
def test_current_and_longest_streaks(offsets, current, longest, total):
    result = count_streaks({TODAY + timedelta(days=n) for n in offsets}, TODAY)
    assert (result["current"], result["longest"], result["total_days"]) == (current, longest, total)
    assert result["counted_today"] == (0 in offsets)


def test_year_boundary_duplicates_and_retroactive_gap_filling():
    today = date(2027, 1, 1)
    dates = {date(2026, 12, 29), date(2026, 12, 31), today, today}
    assert count_streaks(dates, today)["current"] == 2
    dates.add(date(2026, 12, 30))
    assert count_streaks(dates, today)["current"] == 4
    dates.remove(date(2026, 12, 31))
    assert count_streaks(dates, today)["current"] == 1


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"weight_kg": 50},
        {"reps": 8},
        {"weight_kg": -1, "reps": 8},
        {"weight_kg": "50.001", "reps": 8},
        {"weight_kg": 50, "reps": True},
        {"weight_kg": 50, "reps": 8, "distance_m": 10},
        {"distance_m": 0},
        {"distance_m": 10.5},
        {"distance_m": 100, "duration_seconds": 0},
        {"distance_m": 100, "duration_seconds": 21601},
        {"weight_kg": "NaN", "reps": 8},
    ],
)
def test_invalid_metrics_are_rejected(body):
    with pytest.raises(ValueError):
        ExerciseMetricsIn(**body)


@pytest.mark.parametrize(
    "body",
    [
        {"weight_kg": 0, "reps": 30},
        {"weight_kg": "82.25", "reps": 8},
        {"distance_m": 5000},
        {"distance_m": 5000, "duration_seconds": 1800},
    ],
)
def test_valid_metrics(body):
    assert ExerciseMetricsIn(**body)


def test_exercise_name_normalization():
    assert ExerciseCreateIn(name="  Bench\u00a0  Press  ", kind="strength").name == "Bench Press"
    assert ExerciseCreateIn(name="Ｂｅｎｃｈ", kind="strength").name == "Bench"
    for name in ("   ", "a" * 81, "run\u200bning"):
        with pytest.raises(ValueError):
            ExerciseCreateIn(name=name, kind="cardio")
