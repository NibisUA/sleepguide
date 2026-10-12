from datetime import UTC, date, datetime, timedelta

import pytest

from app.analytics.personal import baselines, bedtime_pattern, spearman
from app.analytics.reminders import evening_reminder_day
from app.analytics.sleep_score import Night

TODAY = date(2026, 10, 12)


def night(days, hour=23, minute=0, minutes=480):
    day = TODAY - timedelta(days=days)
    stamp = datetime.combine(
        day - timedelta(days=1) if hour >= 12 else day, datetime.min.time(), tzinfo=UTC
    ).replace(hour=hour, minute=minute)
    return Night(stamp, stamp + timedelta(minutes=minutes), minutes, day)


def test_baseline_nonoverlapping_windows_exclude_today_and_missing():
    nights = [night(i, minutes=420 if i <= 7 else 480) for i in range(1, 36)] + [
        night(0, minutes=1000)
    ]
    result = baselines(TODAY, nights, [], [], [], "UTC")
    sleep = result.metrics[0]
    assert (sleep.recent, sleep.baseline, sleep.delta) == (420, 480, -60)
    assert sleep.recent_days == 7 and sleep.baseline_days == 28 and sleep.ready
    assert result.recent_to < TODAY and result.baseline_to < result.recent_from
    assert result.metrics[3].recent is None and result.metrics[2].baseline is None
    assert result.metrics[1].recent == 0  # zero logged workouts with diary coverage


def test_baseline_sample_threshold_and_stress_daily_weight():
    result = baselines(
        TODAY,
        [night(1)],
        [],
        [(TODAY - timedelta(days=1), 1)] * 10 + [(TODAY - timedelta(days=2), 5)],
        [(TODAY - timedelta(days=1), 0)],
        "UTC",
    )
    assert result.metrics[0].baseline is None and result.metrics[0].delta is None
    assert result.metrics[3].recent == 0 and result.metrics[3].recent_days == 1
    assert result.metrics[2].recent == 3 and result.metrics[2].recent_days == 2


def test_pattern_midnight_and_exact_minimum():
    nights = [night(i, 23, 55) if i % 2 else night(i, 0, 5) for i in range(1, 15)]
    pattern = bedtime_pattern(nights, TODAY, "UTC", True)
    assert pattern.bedtime == "00:00" and pattern.time == "23:30" and pattern.nights == 14
    assert pattern.spread_minutes == 5 and pattern.enabled
    assert bedtime_pattern(nights[:13], TODAY, "UTC").time is None


def test_pattern_ignores_daytime_today_old_and_duplicates():
    nights = [night(i, 14) for i in range(1, 29)] + [night(0), night(29)] + [night(1)] * 20
    pattern = bedtime_pattern(nights, TODAY, "UTC")
    assert pattern.nights == 1 and pattern.time is None


def test_pattern_rejects_irregular_bedtime():
    pattern = bedtime_pattern([night(i, 20 if i % 2 else 2) for i in range(1, 29)], TODAY, "UTC")
    assert pattern.spread_minutes == 180 and pattern.time is None


def test_pattern_short_catchup_and_open_session():
    now = datetime(2026, 10, 12, 23, 35, tzinfo=UTC)
    kwargs = dict(
        now=now,
        tz_name="UTC",
        reminder_time=datetime.min.time().replace(hour=23, minute=30),
        last_sent_date=None,
        has_open_session=False,
        catchup=timedelta(minutes=15),
    )
    assert evening_reminder_day(**kwargs) == TODAY
    assert evening_reminder_day(**{**kwargs, "now": now + timedelta(minutes=10)}) is None
    assert evening_reminder_day(**{**kwargs, "has_open_session": True}) is None
    assert evening_reminder_day(**{**kwargs, "last_sent_date": TODAY}) is None


@pytest.mark.parametrize(
    "a,b,want",
    [
        ([1, 2, 3], [2, 4, 6], 1),
        ([1, 2, 3], [3, 2, 1], -1),
        ([1, 1, 2], [1, 1, 5], 1),
        ([1, 1, 1], [1, 2, 3], None),
        ([1, 2], [3, 4], None),
    ],
)
def test_spearman_ties_and_no_false_zero(a, b, want):
    assert spearman(a, b) == want
