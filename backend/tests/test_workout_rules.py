from datetime import UTC, datetime, timedelta

from app.analytics import workout_rules as w


def dt(*args):
    return datetime(*args, tzinfo=UTC)


def test_workout_limits():
    start = dt(2026, 10, 1, 18, 0)
    assert not w.is_too_long(start, start + timedelta(hours=6))
    assert w.is_too_long(start, start + timedelta(hours=6, minutes=1))


def test_forgotten_stop_threshold():
    start = dt(2026, 10, 1, 18, 0)
    assert not w.needs_end_time(start, start + timedelta(hours=1))
    assert not w.needs_end_time(start, start + timedelta(hours=6))
    assert w.needs_end_time(start, start + timedelta(hours=6, minutes=1))


def test_types_and_intensities_are_fixed_sets():
    assert w.WORKOUT_TYPES == ("gym", "home", "running", "football", "walking", "other")
    assert w.WORKOUT_INTENSITIES == ("easy", "moderate", "hard", "very_hard")
    assert w.DEFAULT_TYPE in w.WORKOUT_TYPES
    assert w.DEFAULT_INTENSITY in w.WORKOUT_INTENSITIES
