"""Real PostgreSQL CRUD, ranking, ownership, races, cascades and progress rules."""

import asyncio
import os
import secrets
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import get_session, get_snapshot_session
from app.core.security import create_access_token
from app.main import app
from app.models import (
    Exercise,
    ExerciseLog,
    ScreenTimeDaily,
    SleepSession,
    StressLog,
    User,
    Workout,
)
from app.services.progress_service import progress

DATABASE = os.environ.get("TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not DATABASE, reason="Requires disposable PostgreSQL *_test DB")


def run_check(check):
    async def run():
        url = make_url(DATABASE)
        if not (url.database or "").endswith("_test"):
            raise RuntimeError("Disposable *_test DB only")
        engine = create_async_engine(url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        ids = []

        async def local_session():
            async with sessions() as session:
                yield session

        async def snapshot():
            async with engine.connect() as connection:
                await connection.execution_options(isolation_level="REPEATABLE READ")
                async with AsyncSession(bind=connection, expire_on_commit=False) as session:
                    yield session

        app.dependency_overrides.clear()
        app.dependency_overrides[get_session] = local_session
        app.dependency_overrides[get_snapshot_session] = snapshot
        try:
            async with sessions() as session:
                users = [
                    User(
                        telegram_user_id=secrets.randbelow(10**12) + 10**12,
                        language="uk",
                        timezone="Europe/Kyiv",
                        sleep_goal_minutes=480,
                    )
                    for _ in range(2)
                ]
                session.add_all(users)
                await session.flush()
                ids.extend(u.id for u in users)
                await session.commit()
            headers = [{"Authorization": f"Bearer {create_access_token(id)}"} for id in ids]
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                await check(client, headers, ids, sessions)
        finally:
            app.dependency_overrides.clear()
            if ids:
                async with sessions() as session:
                    await session.execute(delete(User).where(User.id.in_(ids)))
                    await session.commit()
            await engine.dispose()

    asyncio.run(run())


async def workout(client, headers, days=2):
    start = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0) - timedelta(
        days=days
    )
    result = await client.post(
        "/api/v1/workouts",
        headers=headers,
        json=dict(
            started_at=start.isoformat(),
            ended_at=(start + timedelta(hours=2)).isoformat(),
            type="gym",
            intensity="moderate",
        ),
    )
    assert result.status_code == 201, result.text
    return result.json()


async def exercise(client, headers, name="Bench press", kind="strength"):
    result = await client.post(
        "/api/v1/exercises", headers=headers, json=dict(name=name, kind=kind)
    )
    assert result.status_code == 201, result.text
    return result.json()


async def log(client, headers, workout_id, exercise_id, **metrics):
    result = await client.post(
        f"/api/v1/workouts/{workout_id}/exercises",
        headers=headers,
        json=dict(exercise_id=exercise_id, **metrics),
    )
    assert result.status_code == 201, result.text
    return result.json()


def test_rankings_ties_distance_comparison_edits_and_workout_cascade():
    async def check(c, h, ids, sessions):
        w1, w2 = await workout(c, h[0], 3), await workout(c, h[0], 2)
        strength, cardio = await exercise(c, h[0]), await exercise(c, h[0], "Running", "cardio")
        first = await log(c, h[0], w1["id"], strength["id"], weight_kg="80.50", reps=5)
        await log(c, h[0], w2["id"], strength["id"], weight_kg="80.50", reps=5)
        volume = await log(c, h[0], w2["id"], strength["id"], weight_kg=60, reps=10)
        run5 = await log(c, h[0], w1["id"], cardio["id"], distance_m=5000, duration_seconds=1800)
        await log(c, h[0], w2["id"], cardio["id"], distance_m=5000, duration_seconds=1600)
        await log(c, h[0], w2["id"], cardio["id"], distance_m=1000, duration_seconds=400)
        await log(c, h[0], w2["id"], cardio["id"], distance_m=10000)
        data = (await c.get("/api/v1/records", headers=h[0])).json()
        s = next(row for row in data if row["exercise"]["id"] == strength["id"])
        by = {r["metric"]: r for r in s["records"]}
        assert by["weight"]["value"] == 80.5 and by["weight"]["log_id"] == first["id"]
        assert by["reps"]["value"] == 10 and by["set_volume"]["value"] == 600
        r = next(row for row in data if row["exercise"]["id"] == cardio["id"])
        assert {
            row["distance_m"]: row["value"] for row in r["records"] if row["metric"] == "time"
        } == {1000: 400, 5000: 1600}
        assert next(row for row in r["records"] if row["metric"] == "distance")["value"] == 10000
        renamed = await c.patch(
            f"/api/v1/exercises/{strength['id']}",
            headers=h[0],
            json={"name": "Bench PRESS renamed"},
        )
        assert renamed.status_code == 200, renamed.text
        updated = await c.put(
            f"/api/v1/exercise-logs/{volume['id']}", headers=h[0], json={"weight_kg": 40, "reps": 5}
        )
        assert updated.status_code == 200, updated.text
        s = next(
            row
            for row in (await c.get("/api/v1/records", headers=h[0])).json()
            if row["exercise"]["id"] == strength["id"]
        )
        assert next(row for row in s["records"] if row["metric"] == "set_volume")["value"] == 402.5
        short = await c.patch(
            f"/api/v1/workouts/{w1['id']}",
            headers=h[0],
            json={
                "ended_at": (
                    datetime.fromisoformat(w1["started_at"]) + timedelta(minutes=10)
                ).isoformat()
            },
        )
        assert short.status_code == 422 and short.json()["detail"]["code"] == "exercise_time"
        assert (await c.delete(f"/api/v1/workouts/{w2['id']}", headers=h[0])).status_code == 204
        r = next(
            row
            for row in (await c.get("/api/v1/records", headers=h[0])).json()
            if row["exercise"]["id"] == cardio["id"]
        )
        assert len(r["records"]) == 2
        assert next(row for row in r["records"] if row["metric"] == "time")["log_id"] == run5["id"]

    run_check(check)


def test_owner_isolation_database_fks_export_and_account_erasure():
    async def check(c, h, ids, sessions):
        w = [await workout(c, headers) for headers in h]
        e = [await exercise(c, headers) for headers in h]
        entries = [
            await log(c, h[n], w[n]["id"], e[n]["id"], weight_kg=50, reps=8) for n in range(2)
        ]
        assert len((await c.get("/api/v1/exercises", headers=h[0])).json()) == 1
        assert len((await c.get("/api/v1/records", headers=h[0])).json()) == 1
        for path in (f"/exercises/{e[1]['id']}", f"/exercise-logs/{entries[1]['id']}"):
            assert (await c.delete("/api/v1" + path, headers=h[0])).status_code == 404
        assert (
            await c.get(f"/api/v1/workouts/{w[1]['id']}/exercises", headers=h[0])
        ).status_code == 404
        bad = await c.post(
            f"/api/v1/workouts/{w[0]['id']}/exercises",
            headers=h[0],
            json={"exercise_id": e[1]["id"], "weight_kg": 50, "reps": 8},
        )
        assert bad.status_code == 404
        async with sessions() as session:
            session.add(
                ExerciseLog(
                    user_id=ids[0],
                    exercise_id=e[1]["id"],
                    workout_id=w[0]["id"],
                    weight_kg=50,
                    reps=8,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()
        export = (await c.get("/api/v1/me/export", headers=h[0])).json()
        assert (
            export["schema_version"] == "1.2"
            and len(export["exercises"]) == len(export["exercise_logs"]) == 1
        )
        assert export["exercise_logs"][0]["id"] == entries[0]["id"]
        token = {"Authorization": "Bearer sg_fake"}
        for path in ("/records", "/progress", "/exercises", f"/workouts/{w[0]['id']}/exercises"):
            assert (await c.get("/api/v1" + path, headers=token)).status_code == 401
        assert (
            await c.request("DELETE", "/api/v1/me", headers=h[0], json={"confirm": True})
        ).status_code == 204
        async with sessions() as session:
            for model in (Exercise, ExerciseLog):
                assert (
                    await session.scalar(
                        select(func.count()).select_from(model).where(model.user_id == ids[0])
                    )
                    == 0
                )
                assert (
                    await session.scalar(
                        select(func.count()).select_from(model).where(model.user_id == ids[1])
                    )
                    == 1
                )
        assert (await c.get("/api/v1/records", headers=h[0])).status_code == 401

    run_check(check)


def test_duplicate_name_race_kind_mismatch_and_exercise_cascade():
    async def check(c, h, ids, sessions):
        responses = await asyncio.gather(
            *[
                c.post("/api/v1/exercises", headers=h[0], json={"name": name, "kind": "strength"})
                for name in ("  Bench   press ", "BENCH PRESS")
            ]
        )
        assert sorted(r.status_code for r in responses) == [201, 409]
        e = next(r.json() for r in responses if r.status_code == 201)
        w = await workout(c, h[0])
        wrong = await c.post(
            f"/api/v1/workouts/{w['id']}/exercises",
            headers=h[0],
            json={"exercise_id": e["id"], "distance_m": 5000},
        )
        assert wrong.status_code == 422 and wrong.json()["detail"]["code"] == "exercise_metrics"
        await log(c, h[0], w["id"], e["id"], weight_kg=0, reps=20)
        record = (await c.get("/api/v1/records", headers=h[0])).json()[0]
        assert [r["metric"] for r in record["records"]] == ["reps"]
        assert (await c.delete(f"/api/v1/exercises/{e['id']}", headers=h[0])).status_code == 204
        assert (await c.get(f"/api/v1/workouts/{w['id']}/exercises", headers=h[0])).json() == []
        assert (await c.get(f"/api/v1/workouts/{w['id']}", headers=h[0])).status_code == 200
        running = (await c.post("/api/v1/workouts/start", headers=h[0], json={})).json()
        e = await exercise(c, h[0], "Run", "cardio")
        rejected = await c.post(
            f"/api/v1/workouts/{running['id']}/exercises",
            headers=h[0],
            json={"exercise_id": e["id"], "distance_m": 5000, "duration_seconds": 1800},
        )
        assert rejected.status_code == 409

    run_check(check)


def test_progress_distinct_days_main_sleep_only_and_timezone():
    async def check(c, h, ids, sessions):
        now = datetime(2026, 10, 12, 22, tzinfo=UTC)  # Oct13 in Kyiv
        async with sessions() as session:
            u = await session.get(User, ids[0])
            for n in (0, 1, 2):
                day = now.date() - timedelta(days=n)
                for _ in range(2):
                    session.add(
                        StressLog(
                            user_id=u.id, logged_at=now - timedelta(days=n), local_date=day, level=3
                        )
                    )
            day = now.date()
            session.add(
                SleepSession(
                    user_id=u.id,
                    started_at=now - timedelta(hours=1),
                    ended_at=now,
                    local_date=day,
                    duration_minutes=60,
                    is_nap=True,
                    source="manual",
                )
            )
            session.add(
                Workout(
                    user_id=u.id,
                    started_at=now,
                    local_date=day,
                    type="gym",
                    intensity="easy",
                    source="manual",
                )
            )
            session.add(
                ScreenTimeDaily(
                    user_id=u.id, local_date=day, total_minutes=0, before_bed_minutes=0, source="manual"
                )
            )
            await session.commit()
            result = await progress(session, u, now)
            assert result.today.isoformat() == "2026-10-13"
            by = {r.kind: r for r in result.streaks}
            assert (
                by["all"].current == 3 and by["all"].total_days == 3 and not by["all"].counted_today
            )
            assert by["sleep"].current == by["workout"].current == 0
            assert by["screen"].current == 1
            result = await progress(session, u, now + timedelta(days=1))
            assert result.streaks[0].current == 0 and result.streaks[0].longest == 3
        assert (await c.get("/api/v1/progress", headers=h[1])).json()["streaks"][0]["current"] == 0

    run_check(check)
