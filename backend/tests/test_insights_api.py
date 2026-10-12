from datetime import UTC, datetime, timedelta

from fakes import client_for_token_auth, client_with, default_user

from app.models import Insight, SleepSession
from app.seed.demo import demo_rows
from app.services import insight_service


def demo_results():
    rows = demo_rows(1, "Europe/Kyiv")
    from app.models import ScreenTimeDaily, StressLog, Workout

    return tuple(
        [row for row in rows if isinstance(row, model)]
        for model in (SleepSession, Workout, StressLog, ScreenTimeDaily)
    )


def test_progress_counts_completed_unique_main_sleep_days():
    response = client_with(*demo_results()).get("/api/v1/insights/progress")
    assert response.status_code == 200
    assert response.json() == {
        "days": 60,
        "required_days": 14,
        "minimum_group_days": 5,
        "window_days": 90,
        "ready": True,
        "paired_screen_days": 60,
        "paired_stress_days": 60,
    }


def test_insights_persist_all_four_patterns_with_real_scores():
    client = client_with([1], *demo_results(), [])
    response = client.get("/api/v1/insights")
    assert response.status_code == 200
    assert len(response.json()) == 4
    assert all(row["sample_days"] == 60 for row in response.json())
    assert len(client.sessions[0].added) == 4
    statement = str(client.sessions[0].statements[0])
    assert "FOR UPDATE" in statement
    assert all("user_id" in str(query) for query in client.sessions[0].statements[1:])


def test_empty_dataset_produces_no_insights_and_removes_stale_ones():
    stale = Insight(id=1, user_id=1, type="screen_sleep")
    client = client_with([1], [], [], [], [], [stale])
    response = client.get("/api/v1/insights")
    assert response.json() == []
    assert client.sessions[0].deleted == [stale]


def test_unchanged_findings_preserve_their_timestamp_and_ids():
    first = client_with([1], *demo_results(), []).get("/api/v1/insights").json()
    saved = [
        Insight(
            **{
                **row,
                "user_id": 1,
                "generated_at": datetime.fromisoformat(row["generated_at"].replace("Z", "+00:00")),
                "period_start": datetime.fromisoformat(row["period_start"]).date(),
                "period_end": datetime.fromisoformat(row["period_end"]).date(),
            }
        )
        for row in first
    ]
    client = client_with([1], *demo_results(), saved)
    second = client.get("/api/v1/insights").json()
    assert second == first
    assert client.sessions[0].added == []


def test_naps_and_duplicate_sessions_do_not_inflate_progress():
    nights, _, _, _ = demo_results()
    same = nights[0]
    nap = SleepSession(
        id=9,
        user_id=1,
        started_at=same.started_at,
        ended_at=same.ended_at,
        local_date=same.local_date,
        duration_minutes=120,
        is_nap=True,
        source="retro",
    )
    response = client_with([same, same, nap], [], [], []).get("/api/v1/insights/progress")
    assert response.json()["days"] == 1


def test_insights_require_jwt_and_reject_shortcut_tokens():
    client = client_for_token_auth()
    for path in ("/api/v1/insights", "/api/v1/insights/progress"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers={"Authorization": "Bearer sg_abc"}).status_code == 401


def test_previous_day_join_and_timezone_are_explicit():
    import asyncio

    from fakes import FakeSession

    user = default_user()
    days = asyncio.run(insight_service.observations(FakeSession(*demo_results()), user))
    assert len(days) == 60
    assert {day.bedtime_hour for day in days} == {22, 0}
    for day in days:
        assert (day.before_bed_minutes == 20) == (day.workout_minutes == 45)
        assert (day.before_bed_minutes == 90) == (day.stress_average == 4)


def test_demo_seed_refuses_production(monkeypatch):
    import pytest

    from app.core.config import get_settings
    from app.seed.demo import require_dev

    monkeypatch.setattr(get_settings(), "env", "prod")
    with pytest.raises(RuntimeError, match="ENV=dev"):
        require_dev()


def test_old_and_future_nights_do_not_count():
    nights, _, _, _ = demo_results()
    old = nights[0]
    old.local_date = (datetime.now(UTC) - timedelta(days=95)).date()
    future = nights[1]
    future.local_date = (datetime.now(UTC) + timedelta(days=2)).date()
    result = client_with([old, future], [], [], []).get("/api/v1/insights/progress")
    assert result.json()["days"] == 0


def test_progress_ignores_a_nap_only_day_and_an_open_sleep():
    nights, _, _, _ = demo_results()
    nap = nights[0]
    nap.is_nap = True
    nap.duration_minutes = 120
    running = nights[1]
    running.ended_at = None
    running.duration_minutes = None
    running.local_date = None
    result = client_with([nap, running], [], [], []).get("/api/v1/insights/progress")
    assert result.json()["days"] == 0


def test_daily_stress_uses_unrounded_average_instead_of_peak():
    import asyncio

    from fakes import FakeSession

    from app.models import StressLog

    nights, workouts, stress, screen = demo_results()
    # A single high rating plus a low one is not a high-stress day.
    stress = [
        StressLog(user_id=1, local_date=nights[0].local_date - timedelta(days=1), level=value)
        for value in (5, 2)
    ]
    days = asyncio.run(
        insight_service.observations(FakeSession(nights, workouts, stress, screen), default_user())
    )
    assert days[0].stress_average == 3.5
