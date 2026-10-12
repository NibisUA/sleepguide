"""API tests for the Phase 7 Screen Time endpoints (fake DB session, see fakes.py)."""

from datetime import UTC, date, datetime, timedelta

from fakes import client_with

from app.models import ScreenTimeDaily

NOW = datetime.now(UTC)
TODAY = NOW.date()  # UTC date: never ahead of the user's local date (Kyiv)


def row(day: date, total: int = 300, before_bed: int | None = 30, id: int = 1) -> ScreenTimeDaily:
    return ScreenTimeDaily(
        id=id,
        user_id=1,
        local_date=day,
        total_minutes=total,
        before_bed_minutes=before_bed,
        source="manual",
        updated_at=NOW,
    )


def test_put_creates_a_record_from_the_mini_app_as_manual():
    client = client_with([])  # nothing stored for that day yet
    response = client.put(
        f"/api/v1/screen-time/{TODAY}", json={"total_minutes": 318, "before_bed_minutes": 34}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["local_date"] == str(TODAY)
    assert body["total_minutes"] == 318
    assert body["before_bed_minutes"] == 34
    assert body["source"] == "manual"
    assert len(client.sessions[0].added) == 1  # type: ignore[attr-defined]


def test_put_is_idempotent_and_replaces_the_existing_record():
    existing = row(TODAY, total=100, before_bed=10)
    client = client_with([existing])
    response = client.put(f"/api/v1/screen-time/{TODAY}", json={"total_minutes": 250})
    assert response.status_code == 200
    assert response.json()["total_minutes"] == 250
    assert response.json()["before_bed_minutes"] is None  # replaced, not merged
    assert existing.total_minutes == 250
    assert client.sessions[0].added == []  # type: ignore[attr-defined]  # updated in place


def test_before_bed_is_optional():
    response = client_with([]).put(f"/api/v1/screen-time/{TODAY}", json={"total_minutes": 90})
    assert response.status_code == 200
    assert response.json()["before_bed_minutes"] is None


def test_pre_bed_usage_cannot_exceed_the_total():
    response = client_with().put(
        f"/api/v1/screen-time/{TODAY}", json={"total_minutes": 30, "before_bed_minutes": 60}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_screen_time"


def test_out_of_range_numbers_are_rejected():
    client = client_with()
    url = f"/api/v1/screen-time/{TODAY}"
    assert client.put(url, json={"total_minutes": 1441}).status_code == 422
    assert client.put(url, json={"total_minutes": -1}).status_code == 422
    assert client.put(url, json={"total_minutes": 600, "before_bed_minutes": 121}).status_code == 422
    assert client.put(url, json={}).status_code == 422


def test_the_date_must_be_within_the_last_year_and_not_in_the_future():
    client = client_with()
    for day in (TODAY + timedelta(days=3), TODAY - timedelta(days=400)):
        response = client.put(f"/api/v1/screen-time/{day}", json={"total_minutes": 100})
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "invalid_date"
    assert client.put("/api/v1/screen-time/not-a-date", json={"total_minutes": 1}).status_code == 422


def test_list_returns_records_in_the_range_and_validates_it():
    rows = [row(TODAY - timedelta(days=1), 200, 20, id=1), row(TODAY, 300, 30, id=2)]
    response = client_with(rows).get("/api/v1/screen-time")
    assert response.status_code == 200
    assert [item["total_minutes"] for item in response.json()] == [200, 300]

    client = client_with()
    backwards = client.get("/api/v1/screen-time", params={"from": "2026-10-02", "to": "2026-10-01"})
    assert backwards.status_code == 422
    assert backwards.json()["detail"]["code"] == "invalid_range"
    assert client.get("/api/v1/screen-time", params={"from": "2024-01-01", "to": "2026-10-01"}).status_code == 422


def test_delete_removes_the_day_or_404s():
    existing = row(TODAY)
    client = client_with([existing])
    assert client.delete(f"/api/v1/screen-time/{TODAY}").status_code == 204
    assert client.sessions[0].deleted == [existing]  # type: ignore[attr-defined]
    missing = client_with([]).delete(f"/api/v1/screen-time/{TODAY}")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "screen_time_not_found"
