"""Shared fakes for API tests: no PostgreSQL needed (a queue of query results per request)."""

from datetime import time

from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_export_user, get_user_or_api_token
from app.core import rate_limit
from app.core.db import get_session, get_snapshot_session
from app.main import app
from app.models import SleepSession, User


class FakeResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return list(self._rows)

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class FakeSession:
    """AsyncSession stand-in: returns queued query results and records writes."""

    def __init__(self, *results):
        self.results = list(results)
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.statements: list[object] = []

    async def execute(self, statement):
        self.statements.append(statement)
        if "/* diary-write */" in str(statement):
            return FakeResult([1])
        if not self.results:
            raise AssertionError("Unexpected extra query in FakeSession")
        return FakeResult(self.results.pop(0))

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 999
        self.added.append(obj)

    async def commit(self):
        # SQLAlchemy INSERT applies this column default; the fake has no flush.
        for obj in self.added:
            if isinstance(obj, SleepSession) and obj.is_nap is None:
                obj.is_nap = False

    async def rollback(self):
        pass

    async def delete(self, obj):
        self.deleted.append(obj)


def default_user() -> User:
    return User(
        id=1,
        telegram_user_id=1,
        language="uk",
        timezone="Europe/Kyiv",
        sleep_goal_minutes=480,
        target_bedtime=time(23, 0),
        reminder_morning_on=True,
        reminder_sound_on=True,
        reminder_pattern_on=False,
        weekly_sleep_days=5,
        weekly_workout_days=3,
        weekly_stress_days=3,
        weekly_screen_days=3,
    )


def client_with(*results, user: User | None = None) -> TestClient:
    """A client whose every request gets a fresh FakeSession seeded with `results`."""
    app.dependency_overrides.clear()
    if user is not None:
        # Unsaved SQLAlchemy objects have not received INSERT defaults yet.
        for key, value in (
            ("reminder_sound_on", True),
            ("reminder_pattern_on", False),
            ("weekly_sleep_days", 5),
            ("weekly_workout_days", 3),
            ("weekly_stress_days", 3),
            ("weekly_screen_days", 3),
        ):
            if getattr(user, key) is None:
                setattr(user, key, value)
    created: list[FakeSession] = []

    def make_session() -> FakeSession:
        fake = FakeSession(*results)
        created.append(fake)
        return fake

    app.dependency_overrides[get_session] = make_session
    app.dependency_overrides[get_snapshot_session] = make_session
    app.dependency_overrides[get_current_user] = lambda: user or default_user()
    app.dependency_overrides[get_export_user] = lambda: user or default_user()
    app.dependency_overrides[get_user_or_api_token] = lambda: user or default_user()
    client = TestClient(app)
    client.sessions = created  # type: ignore[attr-defined]
    return client


def client_for_token_auth(*results) -> TestClient:
    """Like `client_with`, but the REAL auth dependencies run (against the fake session).

    Use it to test API-token / JWT authentication itself: queue the token row, then the user row,
    then whatever the endpoint queries.
    """
    app.dependency_overrides.clear()
    rate_limit.reset_limiters()
    created: list[FakeSession] = []

    def make_session() -> FakeSession:
        fake = FakeSession(*results)
        created.append(fake)
        return fake

    app.dependency_overrides[get_session] = make_session
    app.dependency_overrides[get_snapshot_session] = make_session
    client = TestClient(app)
    client.sessions = created  # type: ignore[attr-defined]
    return client
