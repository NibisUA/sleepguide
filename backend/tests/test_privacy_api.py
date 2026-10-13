from datetime import UTC, datetime

import pytest
from fakes import client_for_token_auth, client_with, default_user

from app.models import ApiToken


def owner():
    user = default_user()
    user.created_at = user.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    return user


def test_export_covers_empty_collections_and_never_includes_token_hashes():
    now = datetime.now(UTC)
    token = ApiToken(
        id=1,
        user_id=1,
        label="Phone",
        prefix="sg_hint",
        token_hash="DO_NOT_EXPORT",
        created_at=now,
        last_used_at=None,
        revoked_at=now,
    )
    client = client_with([], [], [], [], [token], [], [], [], [], [], [], user=owner())
    response = client.get("/api/v1/me/export")
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["telegram_user_id"] == 1
    assert set(body) == {
        "schema_version",
        "exported_at",
        "user",
        "sleep_sessions",
        "workouts",
        "stress_logs",
        "screen_time",
        "api_tokens",
        "insights",
        "exercises",
        "exercise_logs",
        "sleep_feedback",
        "workout_templates",
        "deleted_entries",
    }
    assert len(body["api_tokens"]) == 1
    assert body["api_tokens"][0]["revoked_at"] is not None
    assert "DO_NOT_EXPORT" not in response.text and "token_hash" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"].startswith("attachment; filename=")
    assert all("user_id" in str(query) for query in client.sessions[0].statements)


@pytest.mark.parametrize("payload", [None, {}, {"confirm": False}])
def test_deletion_requires_confirmation(payload):
    client = client_with()
    result = client.request("DELETE", "/api/v1/me", json=payload)
    assert result.status_code == 422
    assert not client.sessions[0].deleted


def test_confirmed_deletion_deletes_the_authenticated_owner():
    user = owner()
    client = client_with(user=user)
    response = client.request("DELETE", "/api/v1/me", json={"confirm": True})
    assert response.status_code == 204
    assert client.sessions[0].deleted == [user]


def test_shortcut_tokens_cannot_export_or_delete_an_account():
    client = client_for_token_auth()
    headers = {"Authorization": "Bearer sg_leaked"}
    assert client.get("/api/v1/me/export", headers=headers).status_code == 401
    assert (
        client.request("DELETE", "/api/v1/me", headers=headers, json={"confirm": True}).status_code
        == 401
    )


def test_validation_errors_do_not_echo_sensitive_input():
    response = client_with().post(
        "/api/v1/auth/telegram", json={"init_data": {"secret": "SENSITIVE"}}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "validation_error"
    assert "SENSITIVE" not in response.text
