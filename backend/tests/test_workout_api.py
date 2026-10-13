"""API-level tests for the Phase 5 workout endpoints (fake DB session, see fakes.py)."""

from datetime import UTC, date, datetime, timedelta

from fakes import client_with

from app.models import Workout


def workout_row(
    id: int = 7,
    started_at: datetime | None = None,
    minutes: int | None = None,
    type: str = "gym",
    intensity: str = "moderate",
    local_date: date | None = None,
) -> Workout:
    """A running workout (minutes=None) or a finished one."""
    started = started_at or datetime(2026, 9, 30, 17, 0, tzinfo=UTC)
    return Workout(
        id=id,
        user_id=1,
        started_at=started,
        ended_at=None if minutes is None else started + timedelta(minutes=minutes),
        local_date=local_date or started.date(),
        duration_minutes=minutes,
        type=type,
        intensity=intensity,
        source="manual",
    )


def running_for(minutes: int) -> Workout:
    return workout_row(started_at=datetime.now(UTC) - timedelta(minutes=minutes))


# ---------- start / current / stop ----------


def test_start_creates_a_running_workout_with_the_chosen_type():
    client = client_with([])  # no running workout yet
    response = client.post("/api/v1/workouts/start", json={"type": "running", "intensity": "hard"})
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "running"
    assert body["intensity"] == "hard"
    assert body["ended_at"] is None


def test_start_is_idempotent_when_a_workout_is_already_running():
    existing = running_for(10)
    client = client_with([existing])
    response = client.post("/api/v1/workouts/start", json={"type": "home"})
    assert response.status_code == 200
    assert response.json()["id"] == existing.id
    assert response.json()["type"] == "gym"  # the running workout is returned unchanged


def test_start_rejects_an_unknown_type():
    client = client_with([])
    assert client.post("/api/v1/workouts/start", json={"type": "skydiving"}).status_code == 422


def test_current_returns_null_without_a_running_workout():
    assert client_with([]).get("/api/v1/workouts/current").json() is None


def test_stop_without_a_running_workout_is_404():
    response = client_with([]).post("/api/v1/workouts/stop", json={})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "no_running_workout"


def test_stop_finishes_the_workout_and_corrects_the_intensity():
    client = client_with([running_for(45)], [])
    response = client.post("/api/v1/workouts/stop", json={"intensity": "very_hard"})
    assert response.status_code == 200
    body = response.json()
    assert body["intensity"] == "very_hard"
    assert body["ended_at"] is not None
    assert 44 <= body["duration_minutes"] <= 46


def test_stop_after_six_hours_requires_an_explicit_end_time():
    response = client_with([running_for(7 * 60)]).post("/api/v1/workouts/stop", json={})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "end_time_required"


def test_stop_with_an_explicit_time_beyond_six_hours_is_too_long():
    started = datetime.now(UTC) - timedelta(hours=8)
    ended = (started + timedelta(hours=7)).isoformat()
    client = client_with([workout_row(started_at=started)], [])
    response = client.post("/api/v1/workouts/stop", json={"ended_at": ended})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "too_long"


def test_stop_with_an_explicit_end_time_finishes_a_forgotten_workout():
    started = datetime.now(UTC) - timedelta(hours=8)
    ended = (started + timedelta(minutes=70)).isoformat()
    client = client_with([workout_row(started_at=started)], [])
    response = client.post("/api/v1/workouts/stop", json={"ended_at": ended})
    assert response.status_code == 200
    assert response.json()["duration_minutes"] == 70


def test_stop_immediately_is_rejected_as_shorter_than_a_minute():
    response = client_with([running_for(0)]).post("/api/v1/workouts/stop", json={})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_time"


# ---------- retroactive entry ----------


def test_retroactive_entry_uses_the_local_date_of_the_start():
    client = client_with([])  # no overlap
    response = client.post(
        "/api/v1/workouts",
        json={
            "started_at": "2026-09-30T21:30:00Z",  # 00:30 on Oct 1 in Kyiv
            "ended_at": "2026-09-30T22:30:00Z",
            "type": "football",
            "intensity": "hard",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["local_date"] == "2026-10-01"
    assert body["duration_minutes"] == 60
    assert body["source"] == "retro"


def test_retroactive_entry_rejects_overlaps():
    response = client_with([1]).post(
        "/api/v1/workouts",
        json={
            "started_at": "2026-09-30T17:00:00Z",
            "ended_at": "2026-09-30T18:00:00Z",
            "type": "gym",
            "intensity": "easy",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "overlap"


def test_retroactive_entry_rejects_invalid_and_too_long_intervals():
    base = {"type": "gym", "intensity": "easy"}
    backwards = client_with().post(
        "/api/v1/workouts",
        json={**base, "started_at": "2026-09-30T18:00:00Z", "ended_at": "2026-09-30T17:00:00Z"},
    )
    assert backwards.status_code == 422
    assert backwards.json()["detail"]["code"] == "invalid_time"

    too_long = client_with().post(
        "/api/v1/workouts",
        json={**base, "started_at": "2026-09-30T10:00:00Z", "ended_at": "2026-09-30T17:00:00Z"},
    )
    assert too_long.status_code == 422
    assert too_long.json()["detail"]["code"] == "too_long"


# ---------- history / list / edit / delete ----------


def test_history_fills_every_day_and_sums_counts_and_minutes():
    rows = [
        workout_row(id=1, minutes=60, local_date=date(2026, 9, 29)),
        workout_row(id=2, minutes=30, local_date=date(2026, 9, 29)),
        workout_row(id=3, minutes=45, local_date=date(2026, 10, 1)),
    ]
    response = client_with(rows).get(
        "/api/v1/workouts/history", params={"from": "2026-09-29", "to": "2026-10-01"}
    )
    assert response.status_code == 200
    assert response.json() == [
        {"date": "2026-09-29", "count": 2, "minutes": 90},
        {"date": "2026-09-30", "count": 0, "minutes": 0},
        {"date": "2026-10-01", "count": 1, "minutes": 45},
    ]


def test_history_rejects_a_backwards_or_oversized_range():
    client = client_with()
    backwards = client.get("/api/v1/workouts/history", params={"from": "2026-10-02", "to": "2026-10-01"})
    assert backwards.status_code == 422
    assert backwards.json()["detail"]["code"] == "invalid_range"
    huge = client.get("/api/v1/workouts/history", params={"from": "2024-01-01", "to": "2026-10-01"})
    assert huge.status_code == 422


def test_list_returns_workouts_and_validates_the_limit():
    client = client_with([workout_row(minutes=40)])
    response = client.get("/api/v1/workouts", params={"limit": 10})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert client_with().get("/api/v1/workouts", params={"limit": 0}).status_code == 422


def test_patch_changes_type_and_intensity_of_a_finished_workout():
    row = workout_row(minutes=40, type="gym", intensity="easy")
    client = client_with([row], [])  # the workout, then "no overlap"
    response = client.patch("/api/v1/workouts/7", json={"type": "running", "intensity": "hard"})
    assert response.status_code == 200
    assert response.json()["type"] == "running"
    assert response.json()["intensity"] == "hard"
    assert response.json()["duration_minutes"] == 40


def test_patch_unknown_workout_is_404():
    response = client_with([]).patch("/api/v1/workouts/404", json={"type": "home"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "workout_not_found"


def test_patch_with_an_end_time_finishes_a_running_workout():
    started = datetime.now(UTC) - timedelta(hours=2)
    client = client_with([workout_row(started_at=started)], [], [])
    ended = (started + timedelta(minutes=50)).isoformat()
    response = client.patch("/api/v1/workouts/7", json={"ended_at": ended})
    assert response.status_code == 200
    assert response.json()["duration_minutes"] == 50


def test_delete_returns_204_and_removes_the_row():
    row = workout_row(minutes=30)
    client = client_with([row], [])
    response = client.delete("/api/v1/workouts/7")
    assert response.status_code == 204
    assert client.sessions[0].deleted == [row]  # type: ignore[attr-defined]
    assert client_with([]).delete("/api/v1/workouts/7").status_code == 404
