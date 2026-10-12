from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from test_records_postgres import DATABASE, run_check

from app.models import ScreenTimeDaily, SleepSession, StressLog, User, Workout
from app.services.history_service import overview

pytestmark = pytest.mark.skipif(not DATABASE, reason="Requires disposable PostgreSQL *_test DB")


def test_all_time_more_than_a_year_exact_totals_and_complete_pagination():
    async def check(client, headers, ids, sessions):
        today = datetime.now(UTC).astimezone(ZoneInfo("Europe/Kyiv")).date()
        count = 450
        async with sessions() as session:
            for offset in range(count):
                day = today - timedelta(days=offset)
                sleep_start = datetime.combine(day - timedelta(days=1), time(22), UTC)
                activity = datetime.combine(day, time(12), UTC)
                session.add(
                    SleepSession(
                        user_id=ids[0],
                        started_at=sleep_start,
                        ended_at=sleep_start + timedelta(hours=8),
                        local_date=day,
                        duration_minutes=480,
                        is_nap=False,
                        source="retro",
                    )
                )
                session.add(
                    Workout(
                        user_id=ids[0],
                        started_at=activity,
                        ended_at=activity + timedelta(minutes=30),
                        local_date=day,
                        duration_minutes=30,
                        type="walking",
                        intensity="easy",
                        source="retro",
                    )
                )
                for level in (2, 4):
                    session.add(
                        StressLog(user_id=ids[0], logged_at=activity, local_date=day, level=level)
                    )
                session.add(
                    ScreenTimeDaily(
                        user_id=ids[0],
                        local_date=day,
                        total_minutes=240,
                        before_bed_minutes=0,
                        source="manual",
                    )
                )
            old = today - timedelta(days=2000)
            session.add(
                StressLog(
                    user_id=ids[1],
                    logged_at=datetime.combine(old, time(12), UTC),
                    local_date=old,
                    level=1,
                )
            )
            # Unfinished timers and future data cannot extend the completed history.
            session.add(
                Workout(
                    user_id=ids[0],
                    started_at=datetime.now(UTC),
                    local_date=old,
                    type="gym",
                    intensity="easy",
                    source="manual",
                )
            )
            future = today + timedelta(days=1)
            session.add(
                StressLog(
                    user_id=ids[0],
                    logged_at=datetime.combine(future, time(12), UTC),
                    local_date=future,
                    level=5,
                )
            )
            await session.commit()
        result = await client.get("/api/v1/history?range=all", headers=headers[0])
        assert result.status_code == 200, result.text
        data = result.json()
        assert data["from_date"] == (today - timedelta(days=count - 1)).isoformat()
        assert data["days"] == 450 and data["bucket_days"] == 5 and len(data["points"]) == 90
        assert data["sleep"]["days"] == 450 and data["sleep"]["average_minutes"] == 480
        assert data["workout"] == dict(count=450, minutes=13500)
        assert data["stress"] == dict(count=900, average=3, peak=4)
        assert data["screen"] == dict(days=450, average_total=240, average_before_bed=0)
        params = {"from": data["from_date"], "to": data["to_date"], "limit": 37}
        for kind, field, expected in [
            ("sleep", "sleep_sessions", 450),
            ("workout", "workouts", 450),
            ("stress", "stress_logs", 900),
            ("screen", "screen_time", 450),
        ]:
            seen = []
            cursor = None
            while True:
                page_params = {**params, **({"cursor": cursor} if cursor else {})}
                response = await client.get(
                    f"/api/v1/history/entries/{kind}", headers=headers[0], params=page_params
                )
                assert response.status_code == 200, response.text
                page = response.json()
                assert len(page[field]) <= 37
                seen.extend(
                    row["local_date"] if kind == "screen" else row["id"] for row in page[field]
                )
                cursor = page["next_cursor"]
                if not cursor:
                    break
            assert len(seen) == len(set(seen)) == expected
        shorter = (await client.get("/api/v1/history?range=90d", headers=headers[0])).json()
        assert shorter["days"] == len(shorter["points"]) == 90 and shorter["bucket_days"] == 1
        assert shorter["workout"]["count"] == 90 and shorter["stress"]["count"] == 180
        target = today - timedelta(days=30)
        point = next(row for row in shorter["points"] if row["date"] == target.isoformat())
        score = (await client.get(f"/api/v1/sleep/score/{target}", headers=headers[0])).json()
        assert point["score"] == score["score"]
        other = (await client.get("/api/v1/history?range=all", headers=headers[1])).json()
        assert other["stress"]["count"] == 1 and other["sleep"]["days"] == 0
        assert other["from_date"] == old.isoformat()
        assert result.headers["cache-control"] == "no-store"

    run_check(check)


def test_cursor_survives_boundary_deletion_and_invalid_requests_are_rejected():
    async def check(client, headers, ids, sessions):
        today = datetime.now(UTC).astimezone(ZoneInfo("Europe/Kyiv")).date()
        async with sessions() as session:
            session.add_all(
                [
                    StressLog(
                        user_id=ids[0],
                        local_date=today,
                        logged_at=datetime.combine(today, time(10), UTC),
                        level=2,
                    )
                    for _ in range(45)
                ]
            )
            await session.commit()
        params = {"from": today.isoformat(), "to": today.isoformat(), "limit": 10}
        first = (
            await client.get("/api/v1/history/entries/stress", headers=headers[0], params=params)
        ).json()
        boundary = first["stress_logs"][-1]["id"]
        assert (
            await client.delete(f"/api/v1/stress/{boundary}", headers=headers[0])
        ).status_code == 204
        cursor = first["next_cursor"]
        older = []
        while cursor:
            page = (
                await client.get(
                    "/api/v1/history/entries/stress",
                    headers=headers[0],
                    params={**params, "cursor": cursor},
                )
            ).json()
            older.extend(row["id"] for row in page["stress_logs"])
            cursor = page["next_cursor"]
        assert len(older) == 35 and len(set(older)) == 35 and boundary not in older
        assert not set(older) & {row["id"] for row in first["stress_logs"]}
        empty = await client.get(
            "/api/v1/history/entries/stress", headers=headers[1], params=params
        )
        assert empty.json()["stress_logs"] == []
        for extra in (
            {"limit": 101},
            {"cursor": "bad-cursor!"},
            {"from": (today + timedelta(days=1)).isoformat()},
            {"to": (today + timedelta(days=1)).isoformat()},
        ):
            assert (
                await client.get(
                    "/api/v1/history/entries/stress", headers=headers[0], params={**params, **extra}
                )
            ).status_code == 422
        assert (
            await client.get("/api/v1/history?range=365d", headers=headers[0])
        ).status_code == 422
        token = {"Authorization": "Bearer sg_fake"}
        assert (await client.get("/api/v1/history?range=all", headers=token)).status_code == 401
        assert (
            await client.get("/api/v1/history/entries/sleep", headers=token, params=params)
        ).status_code == 401

    run_check(check)


def test_empty_history_timezone_and_naps_do_not_become_main_sleep():
    async def check(client, headers, ids, sessions):
        empty = (await client.get("/api/v1/history?range=all", headers=headers[0])).json()
        assert (
            not empty["has_data"] and empty["days"] == 1 and empty["sleep"]["average_score"] is None
        )
        assert empty["from_date"] == empty["to_date"]
        now = datetime(2026, 10, 12, 22, tzinfo=UTC)
        day = now.astimezone(ZoneInfo("Europe/Kyiv")).date()
        async with sessions() as session:
            user = await session.get(User, ids[0])
            session.add(
                SleepSession(
                    user_id=user.id,
                    started_at=now - timedelta(hours=1),
                    ended_at=now,
                    local_date=day,
                    duration_minutes=60,
                    is_nap=True,
                    source="manual",
                )
            )
            session.add(
                ScreenTimeDaily(
                    user_id=user.id,
                    local_date=day,
                    total_minutes=0,
                    before_bed_minutes=None,
                    source="manual",
                )
            )
            await session.commit()
            result = await overview(session, user, "all", now)
            assert result.from_date == result.to_date == day
            assert result.has_data and result.sleep.days == 0 and result.sleep.nap_minutes == 60
            assert result.screen.average_total == 0 and result.screen.average_before_bed is None
            fixed = await overview(session, user, "90d", now)
            assert fixed.days == 90 and fixed.from_date == day - timedelta(days=89)
            # No data in a shorter period is correctly reported despite older records.
            past = await overview(session, user, "7d", now - timedelta(days=30))
            assert not past.has_data

    run_check(check)
