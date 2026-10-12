from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from test_records_postgres import DATABASE, run_check

from app.models import SleepSession

pytestmark = pytest.mark.skipif(not DATABASE, reason="Requires disposable PostgreSQL *_test DB")


def test_sparse_history_score_matches_single_day_and_overview():
    async def check(client, headers, ids, sessions):
        today = datetime.now(UTC).astimezone(ZoneInfo("Europe/Kyiv")).date()
        async with sessions() as session:
            for offset in (120, 110, 105, 100, 95, 90, 0):
                day = today - timedelta(days=offset)
                start = datetime.combine(day - timedelta(days=1), time(22), UTC)
                session.add(
                    SleepSession(
                        user_id=ids[0],
                        started_at=start,
                        ended_at=start + timedelta(hours=8),
                        local_date=day,
                        duration_minutes=480,
                        is_nap=False,
                        source="retro",
                    )
                )
            await session.commit()
        score = (await client.get(f"/api/v1/sleep/score/{today}", headers=headers[0])).json()
        legacy = (
            await client.get(
                "/api/v1/sleep/history",
                headers=headers[0],
                params={"from": str(today), "to": str(today)},
            )
        ).json()[0]
        result = (await client.get("/api/v1/history?range=7d", headers=headers[0])).json()
        assert legacy["score"] == score["score"] == result["points"][-1]["score"]
        assert not legacy["score_limited_data"] and not score["limited_data"]

    run_check(check)
