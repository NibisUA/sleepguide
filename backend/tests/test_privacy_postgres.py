"""Real PostgreSQL lifecycle checks, including every cascade and token invalidation."""

import asyncio
import os
import secrets
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.api_tokens import generate_token, hash_token, token_hint
from app.core.db import get_session, get_snapshot_session
from app.core.security import create_access_token
from app.main import app
from app.models import ApiToken, Insight, ScreenTimeDaily, SleepSession, StressLog, User, Workout
from app.seed.demo import demo_rows

DATABASE = os.environ.get("TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not DATABASE, reason="Requires disposable PostgreSQL *_test DB")


def test_export_isolation_and_complete_account_erasure():
    async def run():
        url = make_url(DATABASE)
        if not (url.database or "").endswith("_test"):
            raise RuntimeError("Refusing lifecycle test outside *_test database")
        engine = create_async_engine(url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        ids = []
        app.dependency_overrides.clear()

        async def local_session():
            async with sessions() as session:
                yield session

        async def local_snapshot():
            async with engine.connect() as connection:
                await connection.execution_options(isolation_level="REPEATABLE READ")
                async with AsyncSession(bind=connection, expire_on_commit=False) as session:
                    yield session

        app.dependency_overrides[get_session] = local_session
        app.dependency_overrides[get_snapshot_session] = local_snapshot
        try:
            raw = generate_token()
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
                ids.extend(user.id for user in users)
                for user in users:
                    session.add_all(demo_rows(user.id, user.timezone))
                session.add(
                    ApiToken(
                        user_id=ids[0],
                        token_hash=hash_token(raw),
                        prefix=token_hint(raw),
                        label="Lifecycle",
                        created_at=datetime.now(UTC),
                    )
                )
                await session.commit()
            headers = {"Authorization": f"Bearer {create_access_token(ids[0])}"}
            other_headers = {"Authorization": f"Bearer {create_access_token(ids[1])}"}
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.get("/api/v1/insights", headers=headers)
                export = await client.get("/api/v1/me/export", headers=headers)
                assert export.status_code == 200
                data = export.json()
                assert data["user"]["id"] == ids[0]
                assert (
                    len(data["sleep_sessions"])
                    == len(data["stress_logs"])
                    == len(data["screen_time"])
                    == 60
                )
                assert len(data["workouts"]) == 30 and len(data["insights"]) == 4
                assert len(data["api_tokens"]) == 1
                assert hash_token(raw) not in export.text and raw not in export.text
                assert data["sleep_sessions"][0]["created_at"]
                assert export.headers["cache-control"] == "no-store"
                rejected = await client.request(
                    "DELETE", "/api/v1/me", headers=headers, json={"confirm": False}
                )
                assert rejected.status_code == 422
                assert (await client.get("/api/v1/me", headers=headers)).status_code == 200
                assert (
                    await client.request(
                        "DELETE", "/api/v1/me", headers=headers, json={"confirm": True}
                    )
                ).status_code == 204
                assert (await client.get("/api/v1/me", headers=headers)).status_code == 401
                assert (await client.get("/api/v1/me/export", headers=headers)).status_code == 401
                assert (
                    await client.post(
                        "/api/v1/sleep/start", headers={"Authorization": f"Bearer {raw}"}
                    )
                ).status_code == 401
                assert (await client.get("/api/v1/me/export", headers=other_headers)).json()[
                    "user"
                ]["id"] == ids[1]
            async with sessions() as session:
                for model in (SleepSession, Workout, StressLog, ScreenTimeDaily, ApiToken, Insight):
                    assert (
                        await session.scalar(
                            select(func.count()).select_from(model).where(model.user_id == ids[0])
                        )
                        == 0
                    )
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(SleepSession)
                        .where(SleepSession.user_id == ids[1])
                    )
                    == 60
                )
        finally:
            app.dependency_overrides.clear()
            if ids:
                async with sessions() as session:
                    await session.execute(delete(User).where(User.id.in_(ids)))
                    await session.commit()
            await engine.dispose()

    asyncio.run(run())
