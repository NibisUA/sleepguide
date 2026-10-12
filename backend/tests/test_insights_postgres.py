"""Real persistence / concurrency checks for the disposable PostgreSQL CI service.

Locally: migrate a database named *_test, then set TEST_DATABASE_URL.
No test connects to the deployment database or creates/drops schema.
"""

import asyncio
import os
import secrets

import httpx
import pytest
from sqlalchemy import delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.db import get_session
from app.core.security import create_access_token
from app.main import app
from app.models import Insight, User
from app.seed.demo import demo_rows

DATABASE = os.environ.get("TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not DATABASE, reason="Requires disposable PostgreSQL *_test DB")


def test_persistence_concurrent_refresh_user_isolation_and_cascade():
    async def run():
        url = make_url(DATABASE)
        if not (url.database or "").endswith("_test"):
            raise RuntimeError("Refusing integration tests outside a database named *_test")
        engine = create_async_engine(url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        ids = []
        app.dependency_overrides.clear()

        async def local_session():
            async with sessions() as session:
                yield session

        app.dependency_overrides[get_session] = local_session
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
                ids.extend(user.id for user in users)
                session.add_all(demo_rows(users[0].id, users[0].timezone))
                await session.commit()
            headers = {"Authorization": f"Bearer {create_access_token(ids[0])}"}
            other_headers = {"Authorization": f"Bearer {create_access_token(ids[1])}"}
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                first, second = await asyncio.gather(
                    *[client.get("/api/v1/insights", headers=headers) for _ in range(2)]
                )
                assert first.status_code == second.status_code == 200
                assert first.json() == second.json()
                assert len(first.json()) == 4
                assert len({row["id"] for row in first.json()}) == 4
                assert (await client.get("/api/v1/insights", headers=other_headers)).json() == []
                progress = await client.get("/api/v1/insights/progress", headers=headers)
                assert progress.json()["days"] == 60
                assert (
                    await client.get("/api/v1/insights", headers=headers)
                ).json() == first.json()
            async with sessions() as session:
                assert (
                    len(
                        list(
                            (
                                await session.execute(
                                    select(Insight).where(Insight.user_id == ids[0])
                                )
                            ).scalars()
                        )
                    )
                    == 4
                )
                await session.execute(delete(User).where(User.id == ids[0]))
                await session.commit()
                assert (
                    list(
                        (
                            await session.execute(select(Insight).where(Insight.user_id == ids[0]))
                        ).scalars()
                    )
                    == []
                )
        finally:
            app.dependency_overrides.clear()
            if ids:
                async with sessions() as session:
                    await session.execute(delete(User).where(User.id.in_(ids)))
                    await session.commit()
            await engine.dispose()

    asyncio.run(run())
