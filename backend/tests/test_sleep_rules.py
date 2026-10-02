from datetime import UTC, datetime, timedelta

from app.analytics import sleep_rules as r


def dt(*args):
    return datetime(*args, tzinfo=UTC)


def test_duration_and_nap():
    start, end = dt(2026, 9, 29, 22, 30), dt(2026, 9, 30, 6, 45)
    assert r.duration_minutes(start, end) == 8 * 60 + 15
    assert not r.is_nap(8 * 60 + 15)
    assert r.is_nap(90)
    assert not r.is_nap(180)


def test_local_date_is_wakeup_date_in_user_timezone():
    # 22:30 UTC on Sep 30 is already Oct 1, 01:30 in Kyiv (UTC+3 in summer)
    assert str(r.local_date_of(dt(2026, 9, 30, 22, 30), "Europe/Kyiv")) == "2026-10-01"
    assert str(r.local_date_of(dt(2026, 9, 30, 22, 30), "UTC")) == "2026-09-30"


def test_forgotten_stop_threshold():
    start = dt(2026, 9, 29, 22, 0)
    assert not r.needs_wake_confirmation(start, start + timedelta(hours=10))
    assert not r.needs_wake_confirmation(start, start + timedelta(hours=14))
    assert r.needs_wake_confirmation(start, start + timedelta(hours=14, minutes=1))


def test_end_time_validation():
    start, now = dt(2026, 9, 29, 22, 0), dt(2026, 9, 30, 8, 0)
    assert r.is_valid_end(start, dt(2026, 9, 30, 6, 30), now)
    assert not r.is_valid_end(start, start, now)
    assert not r.is_valid_end(start, dt(2026, 9, 29, 21, 0), now)
    assert not r.is_valid_end(start, now + timedelta(hours=1), now)
