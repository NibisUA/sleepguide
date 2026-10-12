from dataclasses import replace
from datetime import date, timedelta

import pytest

from app.analytics.insights import Observation, analyze


def dataset(count=14):
    return [
        Observation(
            date=date(2026, 1, 1) + timedelta(days=i),
            sleep_minutes=480 if i % 2 else 420,
            score=90 if i % 2 else 70,
            bedtime_hour=23 if i % 2 else 0,
            before_bed_minutes=20 if i % 2 else 90,
            workout_minutes=45 if i % 2 else 0,
            stress_average=2 if i % 2 else 4,
        )
        for i in range(count)
    ]


def test_all_four_rules_show_samples_and_observation_wording():
    findings = {finding.type: finding for finding in analyze(dataset())}
    assert set(findings) == {"screen_sleep", "workout_sleep", "stress_score", "bedtime_score"}
    assert findings["screen_sleep"].message_key.endswith("screen_lower")
    assert findings["workout_sleep"].message_key.endswith("workout_higher")
    assert findings["stress_score"].message_key.endswith("stress_lower")
    assert findings["bedtime_score"].params["from"] == "23:00"
    assert findings["bedtime_score"].params["to"] == "00:00"
    assert all(finding.sample_days == 14 for finding in findings.values())
    assert all(finding.params["group_days"] == 7 for finding in findings.values())


@pytest.mark.parametrize("count", [0, 1, 10, 13])
def test_too_few_distinct_sleep_days_never_unlock(count):
    assert analyze(dataset(count)) == []
    assert analyze(dataset(count) * 3) == []


def test_no_difference_yields_no_patterns():
    assert analyze([replace(day, sleep_minutes=480, score=80) for day in dataset()]) == []


@pytest.mark.parametrize(
    "kind,field,value",
    [
        ("screen_sleep", "before_bed_minutes", 20),
        ("workout_sleep", "workout_minutes", 45),
        ("stress_score", "stress_average", 2),
        ("bedtime_score", "bedtime_hour", 23),
    ],
)
def test_each_rule_requires_five_days_in_each_group(kind, field, value):
    days = dataset()
    # Leave only four entries in the contrasting group.
    days = [replace(day, **{field: value}) if i < 6 else day for i, day in enumerate(days)]
    assert kind not in {finding.type for finding in analyze(days)}


@pytest.mark.parametrize("difference,expected", [(19, False), (20, True), (21, True)])
def test_sleep_difference_boundary(difference, expected):
    days = [
        replace(day, sleep_minutes=480 if i % 2 else 480 - difference)
        for i, day in enumerate(dataset())
    ]
    kinds = {finding.type for finding in analyze(days)}
    assert ("screen_sleep" in kinds) == expected
    assert ("workout_sleep" in kinds) == expected


@pytest.mark.parametrize("difference,expected", [(7, False), (8, True), (9, True)])
def test_score_difference_boundary(difference, expected):
    days = [replace(day, score=80 if i % 2 else 80 - difference) for i, day in enumerate(dataset())]
    kinds = {finding.type for finding in analyze(days)}
    assert ("stress_score" in kinds) == expected
    assert ("bedtime_score" in kinds) == expected


def test_missing_ratings_are_unknown_and_excluded():
    days = [replace(day, before_bed_minutes=None, stress_average=None) for day in dataset()]
    assert {finding.type for finding in analyze(days)} == {"workout_sleep", "bedtime_score"}


def test_direction_is_data_driven_even_if_unexpected():
    days = [
        replace(day, sleep_minutes=960 - day.sleep_minutes, score=160 - day.score)
        for day in dataset()
    ]
    by_type = {finding.type: finding for finding in analyze(days)}
    assert by_type["screen_sleep"].message_key.endswith("_higher")
    assert by_type["workout_sleep"].message_key.endswith("_lower")
    assert by_type["stress_score"].message_key.endswith("_higher")


def test_partial_samples_use_only_paired_days():
    days = dataset(20)
    days = [replace(day, before_bed_minutes=None) if i < 4 else day for i, day in enumerate(days)]
    screen = next(finding for finding in analyze(days) if finding.type == "screen_sleep")
    assert screen.sample_days == 16
    assert screen.period_start == days[4].date


def test_rounding_does_not_push_difference_over_threshold():
    days = dataset(20)
    days = [
        replace(day, sleep_minutes=(480 if i % 2 else 461 if i == 0 else 460))
        for i, day in enumerate(days)
    ]
    assert "screen_sleep" not in {finding.type for finding in analyze(days)}


def test_exactly_five_paired_days_in_each_group_is_enough():
    days = dataset()
    days = [
        replace(day, before_bed_minutes=None, stress_average=None) if i < 4 else day
        for i, day in enumerate(days)
    ]
    by_type = {finding.type: finding for finding in analyze(days)}
    assert by_type["screen_sleep"].sample_days == 10
    assert by_type["stress_score"].sample_days == 10
    assert by_type["screen_sleep"].params["group_days"] == 5


def test_data_order_does_not_change_the_result():
    days = dataset()
    assert analyze(list(reversed(days))) == analyze(days)
