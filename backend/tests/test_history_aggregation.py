from datetime import date, timedelta

import pytest

from app.analytics.history import build_overview
from app.services.errors import DomainError
from app.services.history_service import decode_cursor


@pytest.mark.parametrize("span", [1, 7, 30, 90, 91, 365, 366, 3650, 36500])
def test_chart_points_are_bounded_and_cover_the_entire_period(span):
    start = date(1900, 1, 1)
    end = start + timedelta(days=span - 1)
    result = build_overview(start, end, "all", False, [], [], [], [])
    assert len(result.points) <= 90
    assert result.points[0].date == start and result.points[-1].end_date == end
    for first, second in zip(result.points, result.points[1:]):
        assert first.end_date + timedelta(days=1) == second.date
    assert result.sleep.average_minutes is None and result.stress.average is None


def test_summary_means_use_raw_data_not_averages_of_buckets_or_missing_zeros():
    start = date(2020, 1, 1)
    end = start + timedelta(days=199)
    result = build_overview(
        start,
        end,
        "all",
        True,
        [(start, 480, 30, 80), (end, 600, 0, 100)],
        [(start, 2, 60), (end, 1, 90)],
        [(start, 1, 5, 5), (end, 9, 9, 1)],
        [(start, 0, 0), (start + timedelta(days=1), 600, None), (end, 300, 60)],
    )
    assert result.sleep.average_minutes == 540 and result.sleep.average_score == 90
    assert result.sleep.days == 2 and result.sleep.nap_minutes == 30
    assert result.workout.count == 3 and result.workout.minutes == 150
    assert result.stress.count == 10 and result.stress.average == 1.4 and result.stress.peak == 5
    assert result.screen.days == 3 and result.screen.average_total == 300
    assert result.screen.average_before_bed == 30
    assert result.points[0].screen_before_bed == 0
    assert result.points[1].screen_total is None


@pytest.mark.parametrize("raw", ["not base64!", "W10", "e30", "bnVsbA", "_____"])
def test_malformed_cursors_are_readable_domain_errors(raw):
    with pytest.raises(DomainError) as error:
        decode_cursor(raw, date(2020, 1, 1), date(2026, 1, 1))
    assert error.value.code == "invalid_cursor"
