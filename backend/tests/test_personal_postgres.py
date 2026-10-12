from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from test_records_postgres import DATABASE, run_check

from app.analytics.sleep_rules import local_date_of
from app.bot import reminders as bot_reminders
from app.models import SleepFeedback, SleepSession, User
from app.schemas.privacy import DataExportOut
from scripts.calibrate_score import audit_export

pytestmark = pytest.mark.skipif(not DATABASE, reason="Requires disposable PostgreSQL *_test DB")


def test_pattern_scheduler_claims_once_and_disables_blocked_bot(monkeypatch):
    async def check(c, h, ids, sessions):
        now = datetime(2026, 10, 12, 23, 31, tzinfo=UTC)
        async with sessions() as session:
            user = await session.get(User, ids[0])
            user.timezone = "UTC"
            user.reminder_morning_on = False
            user.reminder_pattern_on = True
            for i in range(1, 15):
                stamp = (now - timedelta(days=i)).replace(hour=0, minute=0)
                session.add(
                    SleepSession(
                        user_id=user.id,
                        started_at=stamp,
                        ended_at=stamp + timedelta(hours=8),
                        local_date=stamp.date(),
                        duration_minutes=480,
                        is_nap=False,
                        source="manual",
                    )
                )
            await session.commit()
        monkeypatch.setattr(bot_reminders, "SessionLocal", sessions)

        class Bot:
            calls = []

            async def send_message(self, *args, **kwargs):
                self.calls.append((args, kwargs))

        bot = Bot()
        assert await bot_reminders.process_due_reminders(bot, now) == 1
        assert await bot_reminders.process_due_reminders(bot, now) == 0
        assert len(bot.calls) == 1
        async with sessions() as session:
            user = await session.get(User, ids[0])
            assert user.last_evening_reminder_date == now.date()
            await bot_reminders._disable_reminders(session, ids[0])
        async with sessions() as session:
            user = await session.get(User, ids[0])
            assert not user.reminder_pattern_on and not user.reminder_morning_on
            assert user.reminder_evening_time is None

    run_check(check)


async def add_nights(sessions, user_id, count=70):
    # Explicitly synthetic fixture, never empirical calibration evidence.
    today = local_date_of(datetime.now(UTC), "Europe/Kyiv")
    async with sessions() as session:
        for i in range(1, count + 1):
            day = today - timedelta(days=i)
            minutes = 360 + (i % 5) * 40
            wake = datetime.combine(day, datetime.min.time(), tzinfo=UTC).replace(hour=5)
            session.add(
                SleepSession(
                    user_id=user_id,
                    started_at=wake - timedelta(minutes=minutes),
                    ended_at=wake,
                    duration_minutes=minutes,
                    local_date=day,
                    is_nap=False,
                    source="manual",
                )
            )
        await session.commit()
    return today


def test_feedback_upsert_isolation_export_and_cascade():
    async def check(c, h, ids, sessions):
        today = await add_nights(sessions, ids[0])
        await add_nights(sessions, ids[1])
        day = (today - timedelta(days=1)).isoformat()
        path = f"/api/v1/personal/feedback/{day}"
        assert (await c.put(path, headers=h[0], json={"rating": 0})).status_code == 422
        assert (await c.put(path, headers=h[0], json={"rating": True})).status_code == 422
        assert (await c.put(path, headers=h[0], json={"rating": 4})).status_code == 200
        assert (await c.put(path, headers=h[0], json={"rating": 2})).json()["rating"] == 2
        assert (await c.get(path, headers=h[1])).json() is None
        assert (await c.delete(path, headers=h[1])).status_code == 204
        assert (await c.get(path, headers=h[0])).json()["rating"] == 2
        assert (
            await c.put(
                f"/api/v1/personal/feedback/{today + timedelta(days=1)}",
                headers=h[0],
                json={"rating": 3},
            )
        ).status_code == 422
        assert (
            await c.put(f"/api/v1/personal/feedback/{today}", headers=h[0], json={"rating": 3})
        ).status_code == 404
        export = (await c.get("/api/v1/me/export", headers=h[0])).json()
        assert export["schema_version"] == "1.2" and len(export["sleep_feedback"]) == 1
        offline = audit_export(DataExportOut.model_validate(export), "synthetic")
        assert offline["eligible_nights"] == 1 and not offline["weights_applied"]
        assert offline["status"] == "insufficient_data"
        assert export["sleep_feedback"][0]["rating"] == 2
        assert export["user"]["weekly_sleep_days"] == 5
        assert (
            await c.request("DELETE", "/api/v1/me", headers=h[0], json={"confirm": True})
        ).status_code == 204
        async with sessions() as session:
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(SleepFeedback)
                    .where(SleepFeedback.user_id == ids[0])
                )
                == 0
            )
        assert (await c.get(path, headers=h[0])).status_code == 401

    run_check(check)


def test_calibration_readiness_stale_context_and_unchanged_formula():
    async def check(c, h, ids, sessions):
        today = await add_nights(sessions, ids[0])
        for i in range(1, 29):
            day = today - timedelta(days=i)
            response = await c.put(
                f"/api/v1/personal/feedback/{day}", headers=h[0], json={"rating": 1 + i % 5}
            )
            assert response.status_code == 200, response.text
        report = (await c.get("/api/v1/personal/calibration", headers=h[0])).json()
        assert report["matched_nights"] == 28 and report["status"] == "ready_for_review"
        assert report["correlation"] is not None and not report["weights_changed"]
        assert report["algorithm_version"] == "1.0"
        await c.patch("/api/v1/me", headers=h[0], json={"sleep_goal_minutes": 500})
        report = (await c.get("/api/v1/personal/calibration", headers=h[0])).json()
        assert (
            report["stale_ratings"] == 28
            and report["matched_nights"] == 0
            and report["correlation"] is None
        )
        day = today - timedelta(days=1)
        assert (
            await c.put(f"/api/v1/personal/feedback/{day}", headers=h[0], json={"rating": 3})
        ).status_code == 200
        report = (await c.get("/api/v1/personal/calibration", headers=h[0])).json()
        assert report["matched_nights"] == 1 and report["stale_ratings"] == 27
        async with sessions() as session:
            row = await session.scalar(
                select(SleepSession).where(
                    SleepSession.user_id == ids[0], SleepSession.local_date == day
                )
            )
            row.started_at -= timedelta(minutes=1)
            row.duration_minutes += 1
            await session.commit()
        assert (await c.get("/api/v1/personal/calibration", headers=h[0])).json()[
            "stale_ratings"
        ] == 28

    run_check(check)


def test_milestones_baselines_preferences_and_jwt_only():
    async def check(c, h, ids, sessions):
        today = await add_nights(sessions, ids[0], 35)
        other = (await c.get("/api/v1/personal/baselines", headers=h[1])).json()
        assert all(m["recent"] is None for m in other["metrics"])
        data = (await c.get("/api/v1/personal/baselines", headers=h[0])).json()
        assert data["metrics"][0]["ready"] and data["metrics"][0]["baseline_days"] == 28
        assert (
            await c.patch("/api/v1/me", headers=h[0], json={"weekly_workout_days": 8})
        ).status_code == 422
        user = (
            await c.patch(
                "/api/v1/me",
                headers=h[0],
                json={"weekly_workout_days": 0, "reminder_pattern_on": True},
            )
        ).json()
        assert user["weekly_workout_days"] == 0 and user["reminder_pattern_on"]
        result = (await c.get("/api/v1/personal/milestones", headers=h[0])).json()
        assert result["week_from"] == (today - timedelta(days=today.weekday())).isoformat()
        assert next(g for g in result["goals"] if g["kind"] == "workout")["target"] == 0
        assert (
            next(a for a in result["achievements"] if a["key"] == "diary30")["earned_on"]
            is not None
        )
        assert all(
            a["earned_on"] is None
            for a in (await c.get("/api/v1/personal/milestones", headers=h[1])).json()[
                "achievements"
            ]
        )
        for endpoint in ("baselines", "milestones", "calibration", f"feedback/{today}"):
            assert (
                await c.get(
                    "/api/v1/personal/" + endpoint, headers={"Authorization": "Bearer sg_fake"}
                )
            ).status_code == 401

    run_check(check)
