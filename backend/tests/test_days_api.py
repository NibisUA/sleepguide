"""API tests for the Phase 8 Daily Summary (fake DB session, see fakes.py).

The summary runs six queries in a fixed order, so every test queues six results:
nights (for the Sleep Score), sleep sessions, workouts, stress (per-day stats), stress records,
screen time.
"""

from datetime import UTC, date, datetime, timedelta

from fakes import client_with

from app.models import ScreenTimeDaily, SleepSession, StressLog, Workout

NOW = datetime.now(UTC)
DAY = (NOW - timedelta(days=2)).date()  # a past day (never ahead of the user's local date)


def night(day: date) -> SleepSession:
    """8 hours of sleep that ended on `day` (22:00-06:00 local time in Kyiv)."""
    ended = datetime(day.year, day.month, day.day, 4, 0, tzinfo=UTC)
    return SleepSession(
        id=1,
        user_id=1,
        started_at=ended - timedelta(hours=8),
        ended_at=ended,
        local_date=day,
        duration_minutes=480,
        is_nap=False,
        source="manual",
    )


def workout(id: int, minutes: int, kind: str = "gym", running: bool = False) -> Workout:
    started = datetime(DAY.year, DAY.month, DAY.day, 15, 0, tzinfo=UTC)
    return Workout(
        id=id,
        user_id=1,
        started_at=started,
        ended_at=None if running else started + timedelta(minutes=minutes),
        local_date=DAY,
        duration_minutes=None if running else minutes,
        type=kind,
        intensity="hard",
        source="manual",
    )


def stress(id: int, level: int, category: str | None = None) -> StressLog:
    return StressLog(
        id=id,
        user_id=1,
        logged_at=datetime(DAY.year, DAY.month, DAY.day, 10 + id, 0, tzinfo=UTC),
        local_date=DAY,
        level=level,
        category=category,
    )


def screen() -> ScreenTimeDaily:
    return ScreenTimeDaily(
        id=1,
        user_id=1,
        local_date=DAY,
        total_minutes=318,
        before_bed_minutes=34,
        source="shortcut",
        updated_at=NOW,
    )


def test_an_empty_day_has_all_four_areas_with_empty_values():
    response = client_with([], [], [], [], [], []).get(f"/api/v1/days/{DAY}")
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == str(DAY)
    assert body["sleep_score"] is None
    assert body["sleep_sessions"] == []
    assert body["workouts"] == [] and body["workout_minutes"] == 0
    assert body["stress"] == {
        "date": str(DAY),
        "count": 0,
        "average": None,
        "max": None,
        "level_sum": 0,
    }
    assert body["stress_logs"] == []
    assert body["screen_time"] is None


def test_a_full_day_combines_sleep_workouts_stress_and_screen_time():
    sleep_row = night(DAY)
    stress_rows = [stress(1, 2, "work"), stress(2, 4), stress(3, 4, "money")]
    response = client_with(
        [sleep_row],  # nights for the score
        [sleep_row],  # sessions of the day
        [workout(1, 60, "running"), workout(2, 30, "gym")],
        stress_rows,  # per-day stress stats
        stress_rows,  # stress records
        [screen()],
    ).get(f"/api/v1/days/{DAY}")
    assert response.status_code == 200
    body = response.json()

    assert body["sleep_score"]["date"] == str(DAY)
    assert body["sleep_score"]["sleep_minutes"] == 480
    assert 0 <= body["sleep_score"]["score"] <= 100
    assert [s["duration_minutes"] for s in body["sleep_sessions"]] == [480]

    assert [w["type"] for w in body["workouts"]] == ["running", "gym"]
    assert body["workout_minutes"] == 90

    assert body["stress"]["count"] == 3
    assert body["stress"]["average"] == 3.3  # (2 + 4 + 4) / 3
    assert body["stress"]["max"] == 4
    assert [log["level"] for log in body["stress_logs"]] == [2, 4, 4]

    assert body["screen_time"]["total_minutes"] == 318
    assert body["screen_time"]["before_bed_minutes"] == 34
    assert body["screen_time"]["source"] == "shortcut"


def test_a_workout_that_is_still_running_is_not_part_of_the_summary():
    response = client_with(
        [], [], [workout(1, 0, running=True), workout(2, 45)], [], [], []
    ).get(f"/api/v1/days/{DAY}")
    body = response.json()
    assert [w["id"] for w in body["workouts"]] == [2]
    assert body["workout_minutes"] == 45


def test_the_future_and_malformed_dates_are_rejected():
    client = client_with()
    future = (NOW + timedelta(days=3)).date()
    response = client.get(f"/api/v1/days/{future}")
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_date"
    assert client.get("/api/v1/days/not-a-date").status_code == 422
