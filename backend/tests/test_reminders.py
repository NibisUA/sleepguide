from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.analytics import reminders as r

KYIV = "Europe/Kyiv"
TZ = ZoneInfo(KYIV)


def kyiv(*args) -> datetime:
    """An aware Kyiv local time converted to UTC (what the scheduler passes as `now`)."""
    return datetime(*args, tzinfo=TZ).astimezone(UTC)


# ---------- evening reminder ----------


def test_evening_due_at_the_scheduled_minute():
    now = kyiv(2026, 10, 1, 22, 30)
    assert r.evening_reminder_day(now, KYIV, time(22, 30), None, False) == date(2026, 10, 1)


def test_evening_not_due_before_the_time():
    now = kyiv(2026, 10, 1, 22, 29)
    assert r.evening_reminder_day(now, KYIV, time(22, 30), None, False) is None


def test_evening_catch_up_window_covers_a_short_outage_but_not_a_long_one():
    assert r.evening_reminder_day(kyiv(2026, 10, 1, 23, 59), KYIV, time(22, 30), None, False) == date(2026, 10, 1)
    # 90 minutes after the schedule it is too late to be useful
    assert r.evening_reminder_day(kyiv(2026, 10, 2, 0, 0), KYIV, time(22, 30), None, False) is None


def test_evening_is_sent_once_per_day():
    now = kyiv(2026, 10, 1, 22, 35)
    assert r.evening_reminder_day(now, KYIV, time(22, 30), date(2026, 10, 1), False) is None
    # yesterday's marker does not block today's reminder
    assert r.evening_reminder_day(now, KYIV, time(22, 30), date(2026, 9, 30), False) == date(2026, 10, 1)


def test_evening_skipped_when_a_session_is_already_running():
    now = kyiv(2026, 10, 1, 22, 30)
    assert r.evening_reminder_day(now, KYIV, time(22, 30), None, True) is None


def test_evening_disabled_without_a_time():
    assert r.evening_reminder_day(kyiv(2026, 10, 1, 22, 30), KYIV, None, None, False) is None


def test_evening_after_midnight_belongs_to_the_previous_day():
    # reminder at 23:30, tick at 00:10 next local day: the schedule's own date is returned
    now = kyiv(2026, 10, 2, 0, 10)
    assert r.evening_reminder_day(now, KYIV, time(23, 30), None, False) == date(2026, 10, 1)
    # ...and the marker for that day prevents a second send after midnight
    assert r.evening_reminder_day(now, KYIV, time(23, 30), date(2026, 10, 1), False) is None


def test_evening_uses_the_users_time_zone():
    # 22:30 in New York is 02:30 UTC next day: not due at 22:30 Kyiv time
    now = kyiv(2026, 10, 1, 22, 30)
    assert r.evening_reminder_day(now, "America/New_York", time(22, 30), None, False) is None
    ny_now = datetime(2026, 10, 1, 22, 30, tzinfo=ZoneInfo("America/New_York")).astimezone(UTC)
    assert r.evening_reminder_day(ny_now, "America/New_York", time(22, 30), None, False) == date(2026, 10, 1)


def test_evening_across_the_autumn_dst_change():
    # Europe/Kyiv leaves summer time on 2026-10-25 (04:00 -> 03:00); 22:30 that night is still unambiguous
    now = kyiv(2026, 10, 25, 22, 30)
    assert r.evening_reminder_day(now, KYIV, time(22, 30), None, False) == date(2026, 10, 25)


# ---------- morning nudge ----------


def started_at_kyiv(*args) -> datetime:
    return kyiv(*args)


def test_morning_nudge_inside_the_window_for_a_plausible_night():
    start = started_at_kyiv(2026, 10, 1, 23, 0)
    assert r.morning_nudge_due(kyiv(2026, 10, 2, 7, 30), KYIV, True, start, None) is True


def test_morning_nudge_not_before_the_local_morning_window():
    start = started_at_kyiv(2026, 10, 1, 21, 0)
    assert r.morning_nudge_due(kyiv(2026, 10, 2, 6, 30), KYIV, True, start, None) is False  # 9.5 h old, too early


def test_morning_nudge_not_after_the_window():
    start = started_at_kyiv(2026, 10, 1, 23, 0)
    assert r.morning_nudge_due(kyiv(2026, 10, 2, 12, 0), KYIV, True, start, None) is False


def test_morning_nudge_needs_a_plausible_age():
    start = started_at_kyiv(2026, 10, 2, 5, 0)
    assert r.morning_nudge_due(kyiv(2026, 10, 2, 8, 0), KYIV, True, start, None) is False  # 3 h
    long_ago = started_at_kyiv(2026, 10, 1, 8, 0)
    assert r.morning_nudge_due(kyiv(2026, 10, 2, 8, 0), KYIV, True, long_ago, None) is False  # 24 h: forgotten Stop


def test_morning_nudge_only_once_per_session():
    start = started_at_kyiv(2026, 10, 1, 23, 0)
    now = kyiv(2026, 10, 2, 8, 0)
    assert r.morning_nudge_due(now, KYIV, True, start, now - timedelta(minutes=30)) is False
    # a nudge sent for a previous night does not suppress this one
    assert r.morning_nudge_due(now, KYIV, True, start, start - timedelta(days=1)) is True


def test_morning_nudge_respects_the_switch_and_missing_session():
    start = started_at_kyiv(2026, 10, 1, 23, 0)
    now = kyiv(2026, 10, 2, 8, 0)
    assert r.morning_nudge_due(now, KYIV, False, start, None) is False
    assert r.morning_nudge_due(now, KYIV, True, None, None) is False
