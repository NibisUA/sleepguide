from unittest.mock import AsyncMock

from fakes import client_for_token_auth

from app import main


def test_health_checks_database_and_reports_outage(monkeypatch):
    class Session:
        execute = AsyncMock()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    session = Session()
    monkeypatch.setattr(main, "SessionLocal", lambda: session)
    client = client_for_token_auth()
    healthy = client.get("/health")
    assert healthy.status_code == 200 and healthy.json() == {"status": "ok", "database": "ok"}
    session.execute.side_effect = TimeoutError()
    failed = client.get("/health")
    assert failed.status_code == 503
    assert failed.json() == {"status": "error", "database": "unavailable"}
    assert failed.headers["cache-control"] == "no-store"
