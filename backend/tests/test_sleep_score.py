from datetime import UTC, date, datetime, time, timedelta

from app.analytics import sleep_score as s


def night(day: date, start_hour: int, start_minute: int, minutes: int) -> s.Night:
    started = datetime(day.year, day.month, day.day, start_hour, start_minute, tzinfo=UTC)
    return s.Night(
        started_at=started,
        ended_at=started + timedelta(minutes=minutes),
        minutes=minutes,
        local_date=day,
    )


def consecutive_nights(
    target: date, durations: list[int], bed_hour: int = 23, bed_minute: int = 0
) -> list[s.Night]:
    """One night per day, ending with ``target``."""
    return [
        night(
            target - timedelta(days=len(durations) - 1 - i),
            bed_hour,
            bed_minute,
            minutes,
        )
        for i, minutes in enumerate(durations)
    ]


def scored(target: date, nights: list[s.Night], **kwargs) -> s.SleepScore:
    result = s.compute_sleep_score(target, nights, **kwargs)
    assert result is not None
    return result


def component(score: s.SleepScore, key: str) -> s.ComponentScore:
    return next(c for c in score.components if c.key == key)


def test_no_sleep_on_date_has_no_score():
    target = date(2026, 9, 30)
    assert s.compute_sleep_score(target, []) is None
    assert s.compute_sleep_score(target, consecutive_nights(date(2026, 9, 29), [420])) is None


def test_duration_scores_against_goal_and_caps_at_goal():
    target = date(2026, 9, 30)
    short = scored(target, [night(target, 23, 0, 420)], goal_minutes=480)
    full = scored(target, [night(target, 23, 0, 480)], goal_minutes=480)
    long = scored(target, [night(target, 23, 0, 600)], goal_minutes=480)

    assert component(short, "duration").earned == 35.0
    assert component(full, "duration").earned == 40.0
    assert component(long, "duration").earned == 40.0
    assert component(short, "duration").detail == {"minutes": 420, "goal_minutes": 480}


def test_cold_start_omits_history_components_and_renormalizes_weights():
    target = date(2026, 9, 30)
    nights = consecutive_nights(target, [480, 480, 480])
    score = scored(target, nights, goal_minutes=480)

    assert score.limited_data
    assert [c.key for c in score.components] == ["duration", "bedtime_timing"]
    assert sum(c.max for c in score.components) == 50
    assert score.score == 100  # 40/40 + 10/10, renormalized
    assert score.sleep_minutes == 480


def test_full_history_scores_all_four_components():
    target = date(2026, 9, 30)
    nights = consecutive_nights(target, [420] * 7)
    score = scored(target, nights, goal_minutes=480)

    assert not score.limited_data
    assert [c.key for c in score.components] == [
        "duration",
        "bedtime_timing",
        "consistency",
        "sleep_debt",
    ]
    assert component(score, "duration").earned == 35.0
    assert component(score, "consistency").earned == 30.0
    assert component(score, "sleep_debt").earned == 2.5  # 7 x 60 min deficit
    assert component(score, "bedtime_timing").earned == 10.0
    # The displayed breakdown always adds up to the score.
    earned = sum(c.earned for c in score.components)
    maximal = sum(c.max for c in score.components)
    assert score.score == round(100 * earned / maximal) == 78


def test_days_without_records_are_not_sleep_debt():
    target = date(2026, 9, 30)
    old = consecutive_nights(target - timedelta(days=7), [480] * 5)
    recent = [night(target, 23, 0, 480), night(target - timedelta(days=1), 23, 0, 480)]
    score = scored(target, old + recent, goal_minutes=480)

    debt = component(score, "sleep_debt")
    assert debt.earned == 20.0
    assert debt.detail["days_counted"] == 2
    assert debt.detail["deficit_minutes"] == 0


def test_consistency_rewards_regular_schedule_and_penalizes_irregular_one():
    target = date(2026, 9, 30)
    regular = scored(target, consecutive_nights(target, [480] * 7), goal_minutes=480)
    assert component(regular, "consistency").earned == 30.0

    irregular = [
        night(target - timedelta(days=6 - i), 22 if i % 2 else 2, 0, 480) for i in range(7)
    ]
    spread = component(scored(target, irregular, goal_minutes=480), "consistency")
    assert spread.earned == 0.4  # ~119 min of spread is almost the zero-score spread
    assert spread.detail["bedtime_spread_minutes"] == 119
    assert spread.detail["wake_spread_minutes"] == 119


def test_bedtime_timing_has_grace_and_zeroes_two_hours_late():
    target = date(2026, 9, 30)
    on_time = scored(target, [night(target, 23, 20, 480)])  # 20 min late: still full
    assert component(on_time, "bedtime_timing").earned == 10.0

    one_hour_late = scored(target, [night(target, 0, 0, 480)])
    assert component(one_hour_late, "bedtime_timing").earned == 6.7

    two_hours_late = scored(target, [night(target, 1, 0, 480)])
    assert component(two_hours_late, "bedtime_timing").earned == 0.0

    early = scored(target, [night(target, 21, 30, 480)])
    assert component(early, "bedtime_timing").earned == 10.0


def test_target_bedtime_is_configurable_and_defaulted():
    target = date(2026, 9, 30)
    custom = scored(target, [night(target, 1, 0, 480)], target_bedtime=time(0, 30))
    assert component(custom, "bedtime_timing").earned == 10.0
    assert component(custom, "bedtime_timing").detail["used_default_target"] is False

    default = scored(target, [night(target, 23, 0, 480)])
    detail = component(default, "bedtime_timing").detail
    assert detail["used_default_target"] is True
    assert detail["target_bedtime"] == "23:00"


def test_bedtime_is_read_in_the_user_timezone():
    # 21:00 UTC on Sep 30 is 00:00 on Oct 1 in Kyiv (UTC+3 in summer 2026).
    local_date = date(2026, 10, 1)
    started = datetime(2026, 9, 30, 21, 0, tzinfo=UTC)
    bedtime_night = s.Night(
        started_at=started,
        ended_at=started + timedelta(minutes=480),
        minutes=480,
        local_date=local_date,
    )
    score = scored(local_date, [bedtime_night], tz_name="Europe/Kyiv")
    detail = component(score, "bedtime_timing").detail
    assert detail["bedtime"] == "00:00"
    assert detail["late_minutes"] == 60
    assert component(score, "bedtime_timing").earned == 6.7
