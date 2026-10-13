from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from test_records_postgres import DATABASE, run_check

from app.analytics.screen_time_rules import valid_categories
from app.models import ScreenTimeDaily


@pytest.mark.parametrize(
    "total,categories,valid",
    [
        (542, dict(social_minutes=326, entertainment_minutes=73, games_minutes=53), True),
        (0, dict(social_minutes=0, entertainment_minutes=None, games_minutes=None), True),
        (10, dict(social_minutes=None, entertainment_minutes=None, games_minutes=None), True),
        (30, dict(social_minutes=31), False),
        (100, dict(social_minutes=70, entertainment_minutes=40), False),
        (100, dict(social_minutes=-1), False),
        (100, dict(social_minutes=True), False),
        (100, dict(social_minutes=1.5), False),
    ],
)
def test_category_validation(total, categories, valid):
    assert valid_categories(total, categories) is valid


@pytest.mark.skipif(not DATABASE, reason="Requires disposable PostgreSQL *_test DB")
def test_categories_persist_partial_updates_clear_export_and_history():
    async def check(c, h, ids, sessions):
        day = (datetime.now(UTC) - timedelta(days=2)).date().isoformat()
        path = f"/api/v1/screen-time/{day}"
        body = dict(
            total_minutes=542,
            before_bed_minutes=30,
            social_minutes=326,
            entertainment_minutes=73,
            games_minutes=53,
        )
        response = await c.put(path, headers=h[0], json=body)
        assert response.status_code == 200, response.text
        assert all(response.json()[key] == value for key, value in body.items())
        legacy = await c.put(path, headers=h[0], json=dict(total_minutes=600))
        assert legacy.status_code == 200 and legacy.json()["social_minutes"] == 326
        assert legacy.json()["before_bed_minutes"] is None
        invalid = await c.put(path, headers=h[0], json=dict(total_minutes=100))
        assert (
            invalid.status_code == 422
            and invalid.json()["detail"]["code"] == "invalid_screen_categories"
        )
        assert (await c.get(f"/api/v1/screen-time?from={day}&to={day}", headers=h[0])).json()[0][
            "total_minutes"
        ] == 600
        cleared = await c.put(path, headers=h[0], json=dict(total_minutes=600, social_minutes=None))
        assert cleared.json()["social_minutes"] is None and cleared.json()["games_minutes"] == 53
        exported = (await c.get("/api/v1/me/export", headers=h[0])).json()["screen_time"][0]
        assert exported["entertainment_minutes"] == 73 and exported["social_minutes"] is None
        assert (await c.get(f"/api/v1/screen-time?from={day}&to={day}", headers=h[1])).json() == []
        assert (
            await c.get(
                "/api/v1/history/entries/screen",
                headers=h[0],
                params={"from": day, "to": day},
            )
        ).json()["screen_time"][0]["games_minutes"] == 53
        for value in (-1, 1441, True, 1.5):
            assert (
                await c.put(path, headers=h[0], json=dict(total_minutes=600, social_minutes=value))
            ).status_code == 422

    run_check(check)


@pytest.mark.skipif(not DATABASE, reason="Requires disposable PostgreSQL *_test DB")
def test_csv_category_roundtrip_legacy_files_and_conflicts():
    async def check(c, h, ids, sessions):
        text = "date,total_minutes,before_bed_minutes,social_minutes,entertainment_minutes,games_minutes\n2026-09-26,542,30,326,73,53\n2026-09-27,10,,0,,\n"
        body = dict(kind="screen", csv=text)
        preview = (await c.post("/api/v1/data/preview", headers=h[0], json=body)).json()
        assert preview["ready"] == 2 and preview["rows"][0]["categories"]["games_minutes"] == 53
        assert (await c.post("/api/v1/data/import", headers=h[0], json=body)).json()[
            "imported"
        ] == 2
        export = (await c.get("/api/v1/data/export/screen", headers=h[0])).json()
        assert "social_minutes" in export["csv"]
        assert (
            await c.post(
                "/api/v1/data/import", headers=h[0], json=dict(kind="screen", csv=export["csv"])
            )
        ).json()["duplicates"] == 2
        legacy = "date,total_minutes,before_bed_minutes\n2026-09-26,542,30\n"
        assert (
            await c.post("/api/v1/data/import", headers=h[0], json=dict(kind="screen", csv=legacy))
        ).json()["duplicates"] == 1
        async with sessions() as s:
            row = await s.scalar(
                select(ScreenTimeDaily).where(
                    ScreenTimeDaily.user_id == ids[0], ScreenTimeDaily.total_minutes == 542
                )
            )
            assert row.social_minutes == 326
        conflict = text.replace(",326,73,53", ",300,73,53")
        assert (
            await c.post(
                "/api/v1/data/preview", headers=h[0], json=dict(kind="screen", csv=conflict)
            )
        ).json()["errors"] == 1
        invalid = text.replace(",326,73,53", ",500,73,53")
        preview = (
            await c.post(
                "/api/v1/data/preview", headers=h[0], json=dict(kind="screen", csv=invalid)
            )
        ).json()
        assert preview["rows"][0]["code"] == "invalid_screen_categories"
        assert (
            await c.post("/api/v1/data/import", headers=h[0], json=dict(kind="screen", csv=invalid))
        ).status_code == 400

    run_check(check)


@pytest.mark.skipif(not DATABASE, reason="Requires disposable PostgreSQL *_test DB")
def test_database_rejects_impossible_category_totals():
    async def check(c, h, ids, sessions):
        async with sessions() as s:
            row = ScreenTimeDaily(
                user_id=ids[0],
                local_date=datetime.now(UTC).date(),
                total_minutes=100,
                social_minutes=101,
            )
            s.add(row)
            with pytest.raises(IntegrityError):
                await s.commit()
            await s.rollback()

    run_check(check)
