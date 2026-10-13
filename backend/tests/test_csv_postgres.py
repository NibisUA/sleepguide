import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from test_records_postgres import DATABASE, exercise, log, run_check, workout

from app.bot import reminders
from app.models import SleepSession, User, Workout

pytestmark = pytest.mark.skipif(not DATABASE, reason="Requires disposable PostgreSQL *_test DB")
SLEEP = "Дата,Час коли заснув,Час коли прокинувся\n26.09.2026,23:30,07:30\n27.09.2026,01:15,09:00\n"


def test_csv_preview_atomic_import_duplicates_history_export_and_owner_isolation():
    async def check(c, h, ids, sessions):
        body = {"kind": "sleep", "csv": SLEEP}
        preview = await c.post("/api/v1/data/preview", headers=h[0], json=body)
        assert preview.status_code == 200, preview.text
        assert preview.json()["ready"] == 2
        assert (await c.get("/api/v1/sleep", headers=h[0])).json() == []
        assert (await c.post("/api/v1/data/import", headers=h[0], json=body)).json()[
            "imported"
        ] == 2
        repeat = (await c.post("/api/v1/data/import", headers=h[0], json=body)).json()
        assert repeat["imported"] == 0 and repeat["duplicates"] == 2
        history = (
            await c.get("/api/v1/sleep/history?from=2026-09-26&to=2026-09-27", headers=h[0])
        ).json()
        assert [day["sleep_minutes"] for day in history] == [480, 465]
        exported = (await c.get("/api/v1/data/export/sleep", headers=h[0])).json()
        assert exported["csv"].startswith("\ufeffДата") and "started_at" in exported["csv"]
        roundtrip = {"kind": "sleep", "csv": exported["csv"]}
        assert (await c.post("/api/v1/data/import", headers=h[0], json=roundtrip)).json()[
            "duplicates"
        ] == 2
        other_export = (await c.get("/api/v1/data/export/sleep", headers=h[1])).json()
        assert len(other_export["csv"].splitlines()) == 1
        assert (await c.post("/api/v1/data/import", headers=h[1], json=roundtrip)).json()[
            "imported"
        ] == 2
        invalid = {
            "kind": "sleep",
            "csv": SLEEP + "28.09.2026,25:00,09:00\n29.09.2026,00:00,08:00\n",
        }
        assert (await c.post("/api/v1/data/preview", headers=h[0], json=invalid)).json()[
            "errors"
        ] == 1
        assert (await c.post("/api/v1/data/import", headers=h[0], json=invalid)).status_code == 400
        assert len((await c.get("/api/v1/sleep", headers=h[0])).json()) == 2
        conflict = {"kind": "sleep", "csv": "date,bedtime,wake_time\n2026-09-26,23:00,08:00\n"}
        assert (await c.post("/api/v1/data/preview", headers=h[0], json=conflict)).json()["rows"][
            0
        ]["code"] == "csv_conflict"
        assert (await c.post("/api/v1/data/preview", json=body)).status_code == 401

    run_check(check)


@pytest.mark.parametrize(
    "kind,text",
    [
        ("workout", "date,start,end,type,intensity\n2026-09-26,18:00,19:00,gym,moderate\n"),
        ("stress", "date,time,level,category\n2026-09-26,18:00,3,work\n"),
        ("screen", "date,total_minutes,before_bed_minutes\n2026-09-26,240,30\n"),
    ],
)
def test_other_diaries_roundtrip(kind, text):
    async def check(c, h, ids, sessions):
        assert (
            await c.post("/api/v1/data/import", headers=h[0], json={"kind": kind, "csv": text})
        ).json()["imported"] == 1
        export = (await c.get(f"/api/v1/data/export/{kind}", headers=h[0])).json()
        response = await c.post(
            "/api/v1/data/import", headers=h[0], json={"kind": kind, "csv": export["csv"]}
        )
        assert response.status_code == 200, response.text
        assert response.json()["duplicates"] == 1

    run_check(check)


def test_concurrent_csv_imports_cannot_create_duplicates():
    async def check(c, h, ids, sessions):
        calls = await asyncio.gather(
            *(
                c.post("/api/v1/data/import", headers=h[0], json={"kind": "sleep", "csv": SLEEP})
                for _ in range(2)
            )
        )
        assert sorted(call.json()["imported"] for call in calls) == [0, 2]
        async with sessions() as s:
            assert (
                await s.scalar(
                    select(func.count())
                    .select_from(SleepSession)
                    .where(SleepSession.user_id == ids[0])
                )
                == 2
            )

    run_check(check)


def test_stress_csv_roundtrip_after_profile_timezone_changes():
    async def check(c, h, ids, sessions):
        text = "logged_at,level,category\n2026-09-26T23:30:15.123456Z,3,work\n"
        assert (
            await c.post("/api/v1/data/import", headers=h[0], json={"kind": "stress", "csv": text})
        ).json()["imported"] == 1
        assert (
            await c.patch("/api/v1/me", headers=h[0], json={"timezone": "America/Los_Angeles"})
        ).status_code == 200
        export = (await c.get("/api/v1/data/export/stress", headers=h[0])).json()
        response = await c.post(
            "/api/v1/data/import", headers=h[0], json={"kind": "stress", "csv": export["csv"]}
        )
        assert response.status_code == 200, response.text
        assert response.json()["duplicates"] == 1

    run_check(check)


def test_sets_can_be_logged_during_workout_and_batch_is_atomic():
    async def check(c, h, ids, sessions):
        ex = await exercise(c, h[0])
        async with sessions() as s:
            row = Workout(
                user_id=ids[0],
                started_at=datetime.now(UTC) - timedelta(hours=1),
                local_date=datetime.now(UTC).date(),
                type="gym",
                intensity="moderate",
            )
            s.add(row)
            await s.commit()
            wid = row.id
        path = f"/api/v1/workouts/{wid}/exercises/batch"
        sets = [{"exercise_id": ex["id"], "weight_kg": "60", "reps": 8}] * 3
        response = await c.post(path, headers=h[0], json={"sets": sets})
        assert response.status_code == 201, response.text
        assert len(response.json()) == 3
        assert (await c.get("/api/v1/records", headers=h[0])).json()[0]["records"] == []
        invalid = sets[:1] + [{"exercise_id": ex["id"], "distance_m": 5000}]
        assert (await c.post(path, headers=h[0], json={"sets": invalid})).status_code == 422
        assert len((await c.get(f"/api/v1/workouts/{wid}/exercises", headers=h[0])).json()) == 3
        assert (await c.post(path, headers=h[1], json={"sets": sets})).status_code == 404
        assert (await c.post(path, headers=h[0], json={"sets": sets * 17})).status_code == 422
        assert (await c.post("/api/v1/workouts/stop", headers=h[0], json={})).status_code == 200
        assert len((await c.get("/api/v1/records", headers=h[0])).json()[0]["rep_bests"]) == 1

    run_check(check)


def test_repetition_bests_compare_the_same_weight():
    async def check(c, h, ids, sessions):
        w, ex = await workout(c, h[0]), await exercise(c, h[0])
        for weight, reps in [(60, 8), (60, 12), (80, 6), (80, 5), (0, 20)]:
            await log(c, h[0], w["id"], ex["id"], weight_kg=weight, reps=reps)
        records = (await c.get("/api/v1/records", headers=h[0])).json()[0]
        assert {r["weight_kg"]: r["reps"] for r in records["rep_bests"]} == {0: 20, 60: 12, 80: 6}

    run_check(check)


def test_finishing_an_open_workout_cannot_truncate_a_logged_effort():
    async def check(c, h, ids, sessions):
        ex = await exercise(c, h[0], "Running", "cardio")
        start = datetime.now(UTC) - timedelta(hours=1)
        async with sessions() as s:
            row = Workout(
                user_id=ids[0],
                started_at=start,
                local_date=start.date(),
                type="running",
                intensity="moderate",
            )
            s.add(row)
            await s.commit()
            wid = row.id
        await log(c, h[0], wid, ex["id"], distance_m=5000, duration_seconds=1800)
        response = await c.post(
            "/api/v1/workouts/stop",
            headers=h[0],
            json={"ended_at": (start + timedelta(minutes=20)).isoformat()},
        )
        assert response.status_code == 422 and response.json()["detail"]["code"] == "exercise_time"
        assert (await c.get(f"/api/v1/workouts/{wid}", headers=h[0])).json()["ended_at"] is None
        assert (await c.post("/api/v1/workouts/stop", headers=h[0], json={})).status_code == 200

    run_check(check)


def test_sound_preference_roundtrip_and_reminder_delivery(monkeypatch):
    async def check(c, h, ids, sessions):
        assert (await c.get("/api/v1/me", headers=h[0])).json()["reminder_sound_on"] is True
        assert (
            await c.patch("/api/v1/me", headers=h[0], json={"reminder_sound_on": False})
        ).json()["reminder_sound_on"] is False
        assert (await c.get("/api/v1/me/export", headers=h[0])).json()["user"][
            "reminder_sound_on"
        ] is False

        class Bot:
            calls = []

            async def send_message(self, *args, **kwargs):
                self.calls.append(kwargs)

        bot = Bot()
        monkeypatch.setattr(reminders, "SEND_DELAY_SECONDS", 0)
        async with sessions() as s:
            user = await s.get(User, ids[0])
            for enabled in (False, True):
                user.reminder_sound_on = enabled
                for kind in ("evening", "morning"):
                    assert await reminders._deliver(s, bot, user, kind)
                    assert bot.calls[-1]["disable_notification"] is not enabled

    run_check(check)
