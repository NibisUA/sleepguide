"""API-level tests for the Phase 3 sleep endpoints.

The database session and the current user are fakes, so these tests need no
PostgreSQL — they exercise routing, response models and DomainError → HTTP
status mapping.
"""

from datetime import UTC, date, datetime, time, timedelta

from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_user_or_api_token
from app.core.db import get_session
from app.main import app
from app.models import SleepSession, User

TODAY = date(2026, 10, 1)


def night_row(day: date, minutes: int = 480, start_hour: int = 23) -> SleepSession:
    started = datetime(day.year, day.month, day.day, start_hour, 0, tzinfo=UTC)
    return SleepSession(
        id=day.toordinal(),
        user_id=1,
        started_at=started,
        ended_at=started + timedelta(minutes=minutes),
        local_date=day,
        duration_minutes=minutes,
        is_nap=False,
        source="manual",
    )


def week_rows(end: date = TODAY, minutes: int = 480) -> list[SleepSession]:
    return [night_row(end - timedelta(days=offset), minutes) for offset in reversed(range(7))]


class FakeResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return list(self._rows)

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class FakeSession:
    """AsyncSession stand-in: returns queued query results and records writes."""

    def __init__(self, *results):
        self.results = list(results)
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.statements: list[object] = []

    async def execute(self, statement):
        self.statements.append(statement)
        if not self.results:
            raise AssertionError("Unexpected extra query in FakeSession")
        return FakeResult(self.results.pop(0))

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 999
        self.added.append(obj)

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def delete(self, obj):
        self.deleted.append(obj)


def client_with(*results, user: User | None = None) -> TestClient:
    app.dependency_overrides.clear()
    if user is not None:
        for key, value in (("reminder_pattern_on", False), ("weekly_sleep_days", 5),
                           ("weekly_workout_days", 3), ("weekly_stress_days", 3), ("weekly_screen_days", 3)):
            if getattr(user, key) is None:
                setattr(user, key, value)
    created: list[FakeSession] = []

    def make_session() -> FakeSession:
        fake = FakeSession(*results)
        created.append(fake)
        return fake

    app.dependency_overrides[get_session] = make_session
    app.dependency_overrides[get_current_user] = lambda: (
        user
        or User(
            id=1,
            telegram_user_id=1,
            language="uk",
            timezone="Europe/Kyiv",
            sleep_goal_minutes=480,
            target_bedtime=time(23, 0),
            reminder_morning_on=True,
        )
    )
    # sleep start/stop also accept API tokens; in these tests the user is faked for both
    app.dependency_overrides[get_user_or_api_token] = app.dependency_overrides[get_current_user]
    client = TestClient(app)
    client.sessions = created  # type: ignore[attr-defined]
    return client


def test_score_returns_breakdown_for_the_night():
    client = client_with(week_rows())
    response = client.get(f"/api/v1/sleep/score/{TODAY}")
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == TODAY.isoformat()
    assert body["score"] > 0
    assert [c["key"] for c in body["components"]] == [
        "duration",
        "bedtime_timing",
        "consistency",
        "sleep_debt",
    ]
    for component in body["components"]:
        assert 0 <= component["earned"] <= component["max"]
    assert body["algorithm_version"] == "1.0"


def test_score_is_null_without_sleep_for_that_date():
    client = client_with([])
    response = client.get("/api/v1/sleep/score/2026-01-01")
    assert response.status_code == 200
    assert response.json() is None


def test_history_returns_one_entry_per_day():
    client = client_with(week_rows())
    response = client.get(
        "/api/v1/sleep/history", params={"from": "2026-09-25", "to": "2026-10-01"}
    )
    assert response.status_code == 200
    days = response.json()
    assert [day["date"] for day in days] == [
        "2026-09-25",
        "2026-09-26",
        "2026-09-27",
        "2026-09-28",
        "2026-09-29",
        "2026-09-30",
        "2026-10-01",
    ]
    assert days[-1]["sleep_minutes"] == 480
    assert days[-1]["score"] is not None
    assert days[0]["score_limited_data"] is True  # only one night of history on Sep 25


def test_history_rejects_ranges_longer_than_a_year():
    client = client_with()
    response = client.get(
        "/api/v1/sleep/history", params={"from": "2025-01-01", "to": "2026-12-31"}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_range"


def test_retroactive_entry_creates_a_completed_session():
    client = client_with([])  # no overlapping session
    response = client.post(
        "/api/v1/sleep",
        json={"started_at": "2026-09-30T20:30:00Z", "ended_at": "2026-10-01T04:30:00Z"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["duration_minutes"] == 480
    assert body["local_date"] == "2026-10-01"  # 07:30 on Oct 1 in Kyiv
    assert body["is_nap"] is False
    assert body["source"] == "retro"


def test_retroactive_entry_marks_short_sleep_as_a_nap():
    client = client_with([])
    response = client.post(
        "/api/v1/sleep",
        json={"started_at": "2026-09-30T12:00:00Z", "ended_at": "2026-09-30T13:30:00Z"},
    )
    assert response.status_code == 201
    assert response.json()["is_nap"] is True


def test_retroactive_entry_rejects_invalid_times():
    client = client_with()
    response = client.post(
        "/api/v1/sleep",
        json={"started_at": "2026-10-01T04:30:00Z", "ended_at": "2026-09-30T20:30:00Z"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_time"


def test_retroactive_entry_rejects_overlaps():
    client = client_with([1])  # the overlap query finds another session
    response = client.post(
        "/api/v1/sleep",
        json={"started_at": "2026-09-30T20:30:00Z", "ended_at": "2026-10-01T04:30:00Z"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "overlap"


def test_open_session_can_be_closed_by_patching_the_end_time():
    row = SleepSession(
        id=7,
        user_id=1,
        started_at=datetime(2026, 9, 30, 21, 0, tzinfo=UTC),
        ended_at=None,
        local_date=None,
        duration_minutes=None,
        is_nap=False,
        source="manual",
    )
    client = client_with([row], [])  # load by id, then overlap check
    response = client.patch("/api/v1/sleep/7", json={"ended_at": "2026-10-01T05:30:00Z"})
    assert response.status_code == 200
    body = response.json()
    assert body["duration_minutes"] == 510
    assert body["local_date"] == "2026-10-01"


def test_patch_reports_unknown_sessions():
    client = client_with([])
    response = client.patch("/api/v1/sleep/5", json={"ended_at": "2026-10-01T05:30:00Z"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "sleep_not_found"


def test_delete_session_returns_204():
    row = night_row(TODAY)
    client = client_with([row])
    response = client.delete(f"/api/v1/sleep/{row.id}")
    assert response.status_code == 204


def test_list_can_filter_by_local_date():
    row = night_row(TODAY)
    client = client_with([row])
    response = client.get("/api/v1/sleep", params={"limit": 5, "date": TODAY.isoformat()})
    assert response.status_code == 200
    assert [session["id"] for session in response.json()] == [row.id]


def test_current_is_null_without_an_open_session():
    client = client_with([])
    response = client.get("/api/v1/sleep/current")
    assert response.status_code == 200
    assert response.json() is None


def test_score_and_history_queries_are_not_truncated_by_a_row_limit():
    """A LIMIT on an ascending query would drop the newest night after ~4 months of data."""
    client = client_with(week_rows())
    assert client.get(f"/api/v1/sleep/score/{TODAY}").status_code == 200
    assert "LIMIT" not in str(client.sessions[0].statements[0])  # type: ignore[attr-defined]

    client = client_with(week_rows())
    response = client.get(
        "/api/v1/sleep/history", params={"from": "2026-09-25", "to": "2026-10-01"}
    )
    assert response.status_code == 200
    assert "LIMIT" not in str(client.sessions[0].statements[0])  # type: ignore[attr-defined]


def test_retroactive_entry_rejects_sessions_longer_than_20_hours():
    client = client_with()
    response = client.post(
        "/api/v1/sleep",
        json={"started_at": "2026-09-29T20:00:00Z", "ended_at": "2026-09-30T20:30:00Z"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "too_long"


def test_stopping_with_an_explicit_time_rejects_sessions_longer_than_20_hours():
    row = SleepSession(
        id=8,
        user_id=1,
        started_at=datetime(2026, 9, 29, 20, 0, tzinfo=UTC),
        ended_at=None,
        local_date=None,
        duration_minutes=None,
        is_nap=False,
        source="manual",
    )
    client = client_with([row])  # the open session
    response = client.post("/api/v1/sleep/stop", json={"ended_at": "2026-09-30T20:30:00Z"})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "too_long"


def test_patch_me_sets_keeps_and_clears_target_bedtime():
    user = User(
        id=1,
        telegram_user_id=1,
        language="uk",
        timezone="Europe/Kyiv",
        sleep_goal_minutes=480,
        target_bedtime=None,
        reminder_morning_on=True,
    )
    client = client_with(user=user)

    response = client.patch("/api/v1/me", json={"target_bedtime": "22:30"})
    assert response.status_code == 200
    assert response.json()["target_bedtime"] == "22:30:00"

    # a patch without the field keeps it
    response = client.patch("/api/v1/me", json={"sleep_goal_minutes": 450})
    assert response.status_code == 200
    assert response.json()["sleep_goal_minutes"] == 450
    assert response.json()["target_bedtime"] == "22:30:00"

    # null clears it (the Score falls back to the default bedtime)
    response = client.patch("/api/v1/me", json={"target_bedtime": None})
    assert response.status_code == 200
    assert response.json()["target_bedtime"] is None


def test_patch_me_rejects_an_unreasonable_sleep_goal():
    client = client_with()
    assert client.patch("/api/v1/me", json={"sleep_goal_minutes": 30}).status_code == 422


def test_patch_me_sets_and_clears_reminders():
    user = User(
        id=1,
        telegram_user_id=1,
        language="uk",
        timezone="Europe/Kyiv",
        sleep_goal_minutes=480,
        target_bedtime=None,
        reminder_evening_time=None,
        reminder_morning_on=True,
    )
    client = client_with(user=user)

    response = client.patch("/api/v1/me", json={"reminder_evening_time": "22:30"})
    assert response.status_code == 200
    assert response.json()["reminder_evening_time"] == "22:30:00"

    # unrelated patches keep the reminder
    response = client.patch("/api/v1/me", json={"reminder_morning_on": False})
    assert response.status_code == 200
    assert response.json()["reminder_morning_on"] is False
    assert response.json()["reminder_evening_time"] == "22:30:00"

    # null switches the evening reminder off
    response = client.patch("/api/v1/me", json={"reminder_evening_time": None})
    assert response.status_code == 200
    assert response.json()["reminder_evening_time"] is None
    assert response.json()["reminder_morning_on"] is False
