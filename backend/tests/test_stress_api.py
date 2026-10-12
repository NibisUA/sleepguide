"""API-level tests for the Phase 6 stress endpoints (fake DB session, see fakes.py)."""

from datetime import UTC, date, datetime, timedelta

from fakes import client_with

from app.models import StressLog


def stress_row(
    id: int = 5,
    level: int = 3,
    category: str | None = None,
    local_date: date = date(2026, 10, 1),
    logged_at: datetime | None = None,
) -> StressLog:
    return StressLog(
        id=id,
        user_id=1,
        logged_at=logged_at or datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        local_date=local_date,
        level=level,
        category=category,
    )


# ---------- create ----------


def test_one_tap_logging_needs_only_a_level():
    response = client_with().post("/api/v1/stress", json={"level": 4})
    assert response.status_code == 201
    body = response.json()
    assert body["level"] == 4
    assert body["category"] is None
    assert body["id"] == 999
    assert body["local_date"]  # the local date is computed on the server in the user's time zone


def test_logging_with_a_category_and_an_explicit_time_uses_the_local_date():
    response = client_with().post(
        "/api/v1/stress",
        json={"level": 2, "category": "work", "logged_at": "2026-09-30T21:30:00Z"},  # 00:30 Oct 1 Kyiv
    )
    assert response.status_code == 201
    body = response.json()
    assert body["category"] == "work"
    assert body["local_date"] == "2026-10-01"


def test_levels_outside_one_to_five_are_rejected():
    client = client_with()
    for level in (0, 6, -1):
        assert client.post("/api/v1/stress", json={"level": level}).status_code == 422
    assert client.post("/api/v1/stress", json={}).status_code == 422


def test_unknown_category_is_rejected():
    assert client_with().post("/api/v1/stress", json={"level": 3, "category": "weather"}).status_code == 422


def test_a_rating_in_the_future_is_rejected():
    future = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    response = client_with().post("/api/v1/stress", json={"level": 3, "logged_at": future})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_time"


# ---------- history / list ----------


def test_history_fills_every_day_with_count_average_max_and_sum():
    rows = [
        stress_row(id=1, level=2, local_date=date(2026, 9, 29)),
        stress_row(id=2, level=4, local_date=date(2026, 9, 29)),
        stress_row(id=3, level=5, local_date=date(2026, 10, 1)),
        stress_row(id=4, level=4, local_date=date(2026, 10, 1)),
        stress_row(id=5, level=4, local_date=date(2026, 10, 1)),
    ]
    response = client_with(rows).get(
        "/api/v1/stress/history", params={"from": "2026-09-29", "to": "2026-10-01"}
    )
    assert response.status_code == 200
    assert response.json() == [
        {"date": "2026-09-29", "count": 2, "average": 3.0, "max": 4, "level_sum": 6},
        {"date": "2026-09-30", "count": 0, "average": None, "max": None, "level_sum": 0},
        {"date": "2026-10-01", "count": 3, "average": 4.3, "max": 5, "level_sum": 13},
    ]


def test_history_rejects_a_backwards_or_oversized_range():
    client = client_with()
    backwards = client.get("/api/v1/stress/history", params={"from": "2026-10-02", "to": "2026-10-01"})
    assert backwards.status_code == 422
    assert backwards.json()["detail"]["code"] == "invalid_range"
    huge = client.get("/api/v1/stress/history", params={"from": "2024-01-01", "to": "2026-10-01"})
    assert huge.status_code == 422


def test_list_returns_ratings_and_validates_the_limit():
    response = client_with([stress_row(level=4, category="money")]).get("/api/v1/stress")
    assert response.status_code == 200
    assert response.json()[0]["category"] == "money"
    assert client_with().get("/api/v1/stress", params={"limit": 0}).status_code == 422
    assert client_with().get("/api/v1/stress", params={"limit": 501}).status_code == 422


# ---------- edit / delete ----------


def test_patch_changes_the_level_and_keeps_the_category():
    client = client_with([stress_row(level=2, category="work")])
    response = client.patch("/api/v1/stress/5", json={"level": 5})
    assert response.status_code == 200
    assert response.json()["level"] == 5
    assert response.json()["category"] == "work"


def test_patch_with_null_category_clears_it_and_omitting_it_keeps_it():
    cleared = client_with([stress_row(category="work")]).patch("/api/v1/stress/5", json={"category": None})
    assert cleared.status_code == 200
    assert cleared.json()["category"] is None

    kept = client_with([stress_row(category="work")]).patch("/api/v1/stress/5", json={"level": 4})
    assert kept.json()["category"] == "work"


def test_patch_can_move_a_rating_to_another_day():
    client = client_with([stress_row(local_date=date(2026, 10, 1))])
    response = client.patch("/api/v1/stress/5", json={"logged_at": "2026-09-28T10:00:00Z"})
    assert response.status_code == 200
    assert response.json()["local_date"] == "2026-09-28"


def test_patch_rejects_the_future_and_unknown_records():
    future = (datetime.now(UTC) + timedelta(hours=3)).isoformat()
    response = client_with([stress_row()]).patch("/api/v1/stress/5", json={"logged_at": future})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_time"

    missing = client_with([]).patch("/api/v1/stress/404", json={"level": 2})
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "stress_not_found"


def test_delete_returns_204_and_removes_the_row():
    row = stress_row()
    client = client_with([row])
    assert client.delete("/api/v1/stress/5").status_code == 204
    assert client.sessions[0].deleted == [row]  # type: ignore[attr-defined]
    assert client_with([]).delete("/api/v1/stress/5").status_code == 404
