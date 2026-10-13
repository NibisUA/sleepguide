import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from test_records_postgres import DATABASE, exercise, log, run_check, workout

from app.models import ExerciseLog, Workout
from app.models.saved import DeletedEntry, WorkoutTemplate

pytestmark = pytest.mark.skipif(not DATABASE, reason="Requires disposable PostgreSQL *_test DB")


async def trash(c, header, kind):
    rows = (await c.get("/api/v1/trash", headers=header)).json()
    return next(row for row in rows if row["kind"] == kind)


def test_template_repeat_is_a_plan_not_results_and_survives_source_deletion():
    async def check(c, h, ids, sessions):
        w = await workout(c, h[0])
        ex = await exercise(c, h[0])
        await log(c, h[0], w["id"], ex["id"], weight_kg="80.50", reps=5)
        await log(c, h[0], w["id"], ex["id"], weight_kg="75", reps=8)
        response = await c.post(
            "/api/v1/workout-templates",
            headers=h[0],
            json=dict(name=" Upper body ", workout_id=w["id"]),
        )
        assert response.status_code == 201, response.text
        template = response.json()
        assert template["name"] == "Upper body" and len(template["sets"]) == 2
        assert (await c.get("/api/v1/workout-templates", headers=h[1])).json() == []
        assert (
            await c.post(f"/api/v1/workout-templates/{template['id']}/start", headers=h[1])
        ).status_code == 404
        repeated = await c.post(f"/api/v1/workouts/{w['id']}/repeat", headers=h[0])
        assert repeated.status_code == 200, repeated.text
        plan = repeated.json()
        assert plan["id"] != w["id"] and plan["ended_at"] is None
        assert plan["planned_sets"] == template["sets"]
        assert (await c.get(f"/api/v1/workouts/{plan['id']}/exercises", headers=h[0])).json() == []
        assert (
            await c.post(f"/api/v1/workout-templates/{template['id']}/start", headers=h[0])
        ).status_code == 409
        await c.delete(f"/api/v1/workouts/{plan['id']}", headers=h[0])
        await c.delete(f"/api/v1/workouts/{w['id']}", headers=h[0])
        started = await c.post(f"/api/v1/workout-templates/{template['id']}/start", headers=h[0])
        assert started.status_code == 200 and started.json()["planned_sets"] == template["sets"]
        exported = (await c.get("/api/v1/me/export", headers=h[0])).json()
        assert exported["workout_templates"][0]["sets"] == template["sets"]
        assert len(exported["deleted_entries"]) == 2

    run_check(check)


def test_empty_unfinished_and_missing_exercise_plans_are_rejected():
    async def check(c, h, ids, sessions):
        w = await workout(c, h[0])
        assert (
            await c.post(
                "/api/v1/workout-templates",
                headers=h[0],
                json=dict(name="Empty", workout_id=w["id"]),
            )
        ).status_code == 422
        ex = await exercise(c, h[0])
        await log(c, h[0], w["id"], ex["id"], weight_kg=0, reps=10)
        template = (
            await c.post(
                "/api/v1/workout-templates",
                headers=h[0],
                json=dict(name="Plan", workout_id=w["id"]),
            )
        ).json()
        await c.delete(f"/api/v1/exercises/{ex['id']}", headers=h[0])
        assert (
            await c.post(f"/api/v1/workout-templates/{template['id']}/start", headers=h[0])
        ).json()["detail"]["code"] == "template_missing_exercise"
        deleted = await trash(c, h[0], "exercise")
        assert (
            await c.post(f"/api/v1/trash/{deleted['id']}/restore", headers=h[0])
        ).status_code == 204
        started = (
            await c.post(f"/api/v1/workout-templates/{template['id']}/start", headers=h[0])
        ).json()
        response = await c.post(
            "/api/v1/workout-templates",
            headers=h[0],
            json=dict(name="Open", workout_id=started["id"]),
        )
        assert response.status_code == 409

    run_check(check)


def test_restore_workout_restores_exact_sets_ids_and_records_atomically():
    async def check(c, h, ids, sessions):
        w = await workout(c, h[0])
        ex = await exercise(c, h[0])
        result = await log(c, h[0], w["id"], ex["id"], weight_kg="82.75", reps=5)
        await c.delete(f"/api/v1/workouts/{w['id']}", headers=h[0])
        deleted = await trash(c, h[0], "workout")
        assert deleted["record_id"] == w["id"] and "payload" not in deleted
        assert (
            await c.post(f"/api/v1/trash/{deleted['id']}/restore", headers=h[1])
        ).status_code == 404
        assert (
            await c.post(f"/api/v1/trash/{deleted['id']}/restore", headers=h[0])
        ).status_code == 204
        assert (await c.get(f"/api/v1/workouts/{w['id']}/exercises", headers=h[0])).json() == [
            result
        ]
        assert (await c.get("/api/v1/records", headers=h[0])).json()[0]["records"]
        assert (
            await c.post(f"/api/v1/trash/{deleted['id']}/restore", headers=h[0])
        ).status_code == 404

    run_check(check)


@pytest.mark.parametrize("kind", ["sleep", "stress", "screen"])
def test_restore_other_diaries_and_screen_categories(kind):
    async def check(c, h, ids, sessions):
        now = datetime.now(UTC) - timedelta(days=2)
        day = now.date().isoformat()
        if kind == "sleep":
            response = await c.post(
                "/api/v1/sleep",
                headers=h[0],
                json=dict(
                    started_at=now.isoformat(), ended_at=(now + timedelta(hours=8)).isoformat()
                ),
            )
            row = response.json()
            path = f"/api/v1/sleep/{row['id']}"
        elif kind == "stress":
            row = (
                await c.post(
                    "/api/v1/stress", headers=h[0], json=dict(level=4, logged_at=now.isoformat())
                )
            ).json()
            path = f"/api/v1/stress/{row['id']}"
        else:
            row = (
                await c.put(
                    f"/api/v1/screen-time/{day}",
                    headers=h[0],
                    json=dict(
                        total_minutes=90,
                        social_minutes=30,
                        entertainment_minutes=20,
                        games_minutes=0,
                    ),
                )
            ).json()
            path = f"/api/v1/screen-time/{day}"
        assert (await c.delete(path, headers=h[0])).status_code == 204
        deleted = await trash(c, h[0], kind)
        assert (
            await c.post(f"/api/v1/trash/{deleted['id']}/restore", headers=h[0])
        ).status_code == 204
        exported = (await c.get("/api/v1/me/export", headers=h[0])).json()
        collection = {"sleep": "sleep_sessions", "stress": "stress_logs", "screen": "screen_time"}[
            kind
        ]
        restored = exported[collection][0]
        assert all(restored[key] == value for key, value in row.items())

    run_check(check)


def test_restore_conflicts_never_overwrite_new_data_or_lose_snapshot():
    async def check(c, h, ids, sessions):
        w = await workout(c, h[0])
        ex = await exercise(c, h[0])
        await log(c, h[0], w["id"], ex["id"], weight_kg=80, reps=5)
        await c.delete(f"/api/v1/workouts/{w['id']}", headers=h[0])
        deleted = await trash(c, h[0], "workout")
        new = await workout(c, h[0])
        assert (
            await c.post(f"/api/v1/trash/{deleted['id']}/restore", headers=h[0])
        ).status_code == 409
        assert (await c.get(f"/api/v1/workouts/{new['id']}", headers=h[0])).status_code == 200
        await c.delete(f"/api/v1/workouts/{new['id']}", headers=h[0])
        await c.delete(f"/api/v1/exercises/{ex['id']}", headers=h[0])
        # Missing child dependency rolls back the parent INSERT too.
        assert (
            await c.post(f"/api/v1/trash/{deleted['id']}/restore", headers=h[0])
        ).status_code == 409
        async with sessions() as session:
            assert await session.get(Workout, w["id"]) is None
            assert await session.get(DeletedEntry, deleted["id"]) is not None

    run_check(check)


def test_expiry_permanent_deletion_and_account_cascade():
    async def check(c, h, ids, sessions):
        w = await workout(c, h[0])
        ex = await exercise(c, h[0])
        await log(c, h[0], w["id"], ex["id"], weight_kg=60, reps=10)
        await c.post(
            "/api/v1/workout-templates", headers=h[0], json=dict(name="Routine", workout_id=w["id"])
        )
        await c.delete(f"/api/v1/workouts/{w['id']}", headers=h[0])
        deleted = await trash(c, h[0], "workout")
        async with sessions() as session:
            entry = await session.get(DeletedEntry, deleted["id"])
            entry.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await session.commit()
        assert (
            await c.post(f"/api/v1/trash/{deleted['id']}/restore", headers=h[0])
        ).status_code == 404
        assert (await c.get("/api/v1/trash", headers=h[0])).json() == []
        await c.delete(f"/api/v1/exercises/{ex['id']}", headers=h[0])
        entry = await trash(c, h[0], "exercise")
        assert (await c.delete(f"/api/v1/trash/{entry['id']}", headers=h[1])).status_code == 404
        assert (await c.delete(f"/api/v1/trash/{entry['id']}", headers=h[0])).status_code == 204
        await c.request("DELETE", "/api/v1/me", headers=h[0], json={"confirm": True})
        async with sessions() as session:
            for model in (DeletedEntry, WorkoutTemplate):
                assert not list(await session.scalars(select(model).where(model.user_id == ids[0])))

    run_check(check)


def test_restore_set_after_parent_shrink_keeps_it_in_trash():
    async def check(c, h, ids, sessions):
        w = await workout(c, h[0])
        ex = await exercise(c, h[0], "Run", "cardio")
        result = await log(c, h[0], w["id"], ex["id"], distance_m=5000, duration_seconds=1800)
        await c.delete(f"/api/v1/exercise-logs/{result['id']}", headers=h[0])
        entry = await trash(c, h[0], "exercise_log")
        end = datetime.fromisoformat(w["started_at"]) + timedelta(minutes=10)
        assert (
            await c.patch(
                f"/api/v1/workouts/{w['id']}", headers=h[0], json={"ended_at": end.isoformat()}
            )
        ).status_code == 200
        assert (
            await c.post(f"/api/v1/trash/{entry['id']}/restore", headers=h[0])
        ).status_code == 409
        async with sessions() as session:
            assert await session.get(ExerciseLog, result["id"]) is None
            assert await session.get(DeletedEntry, entry["id"]) is not None

    run_check(check)


def test_concurrent_repeat_starts_only_one_workout():
    async def check(c, h, ids, sessions):
        w = await workout(c, h[0])
        ex = await exercise(c, h[0])
        await log(c, h[0], w["id"], ex["id"], weight_kg=60, reps=10)
        responses = await asyncio.gather(
            *(c.post(f"/api/v1/workouts/{w['id']}/repeat", headers=h[0]) for _ in range(2))
        )
        assert sorted(r.status_code for r in responses) == [200, 409]

    run_check(check)
