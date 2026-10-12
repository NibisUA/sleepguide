"""API tests for personal API tokens and token authentication (fake DB session, see fakes.py)."""

from datetime import UTC, datetime, timedelta

from fakes import client_for_token_auth, client_with, default_user

from app.core import api_tokens, rate_limit
from app.core.rate_limit import SlidingWindowLimiter
from app.models import ApiToken

NOW = datetime.now(UTC)
TODAY = NOW.date().isoformat()  # UTC date: never ahead of the user's local date


def token_row(raw: str | None = None, id: int = 3, label: str = "iPhone") -> tuple[ApiToken, str]:
    raw = raw or api_tokens.generate_token()
    row = ApiToken(
        id=id,
        user_id=1,
        token_hash=api_tokens.hash_token(raw),
        prefix=api_tokens.token_hint(raw),
        label=label,
        created_at=NOW - timedelta(days=1),
        last_used_at=None,
        revoked_at=None,
    )
    return row, raw


def bearer(raw: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {raw}"}


# ---------- managing tokens (session JWT) ----------


def test_creating_a_token_returns_the_secret_once_and_stores_only_its_hash():
    client = client_with([])  # no active tokens yet
    response = client.post("/api/v1/me/api-tokens", json={"label": "  iPhone  "})
    assert response.status_code == 201
    body = response.json()
    assert body["token"].startswith("sg_")
    assert body["label"] == "iPhone"  # trimmed
    assert body["prefix"] == body["token"][:8]

    stored = client.sessions[0].added[0]  # type: ignore[attr-defined]
    assert stored.token_hash == api_tokens.hash_token(body["token"])
    assert stored.token_hash != body["token"]
    assert not hasattr(stored, "token")  # the raw secret is never an attribute of the row


def test_listing_never_exposes_the_secret_or_its_hash():
    row, raw = token_row()
    response = client_with([row]).get("/api/v1/me/api-tokens")
    assert response.status_code == 200
    item = response.json()[0]
    assert set(item) == {"id", "label", "prefix", "created_at", "last_used_at"}
    assert raw not in response.text and row.token_hash not in response.text


def test_label_is_required_and_limited():
    client = client_with([])
    assert client.post("/api/v1/me/api-tokens", json={"label": "   "}).status_code == 422
    assert client.post("/api/v1/me/api-tokens", json={"label": "x" * 41}).status_code == 422
    assert client.post("/api/v1/me/api-tokens", json={}).status_code == 422


def test_at_most_ten_active_tokens():
    rows = [token_row(id=i)[0] for i in range(1, 11)]
    response = client_with(rows).post("/api/v1/me/api-tokens", json={"label": "one more"})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "too_many_tokens"


def test_revoking_marks_the_token_and_unknown_ones_are_404():
    row, _ = token_row()
    assert client_with([row]).delete("/api/v1/me/api-tokens/3").status_code == 204
    assert row.revoked_at is not None
    missing = client_with([]).delete("/api/v1/me/api-tokens/3")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "api_token_not_found"


# ---------- authenticating with a token ----------


def test_a_valid_token_can_submit_screen_time_and_the_source_is_shortcut():
    row, raw = token_row()
    client = client_for_token_auth([row], [default_user()], [])  # token, owner, no existing day
    response = client.put(
        f"/api/v1/screen-time/{TODAY}",
        json={"total_minutes": 318, "before_bed_minutes": 34},
        headers=bearer(raw),
    )
    assert response.status_code == 200
    assert response.json()["source"] == "shortcut"
    assert client.sessions[0].added[0].source == "shortcut"  # type: ignore[attr-defined]
    assert row.last_used_at is not None


def test_a_valid_token_can_start_sleep_and_the_session_is_marked_as_shortcut():
    row, raw = token_row()
    client = client_for_token_auth([row], [default_user()], [])  # token, owner, no open session
    response = client.post("/api/v1/sleep/start", headers=bearer(raw))
    assert response.status_code == 200
    assert client.sessions[0].added[0].source == "shortcut"  # type: ignore[attr-defined]


def test_unknown_or_revoked_tokens_are_rejected():
    # a revoked token is filtered out by the query, exactly like an unknown one
    client = client_for_token_auth([])
    response = client.post("/api/v1/sleep/start", headers=bearer(api_tokens.generate_token()))
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_token"


def test_a_request_without_credentials_is_rejected():
    response = client_for_token_auth().post("/api/v1/sleep/start")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "not_authenticated"


def test_a_token_is_not_accepted_outside_its_scope():
    row, raw = token_row()
    client = client_for_token_auth([row], [default_user()])
    for method, path in (
        ("get", "/api/v1/me"),
        ("get", "/api/v1/me/api-tokens"),
        ("post", "/api/v1/me/api-tokens"),
        ("get", "/api/v1/sleep/current"),
        ("get", "/api/v1/screen-time"),
        ("delete", f"/api/v1/screen-time/{TODAY}"),
    ):
        kwargs = {"json": {"label": "x"}} if method == "post" else {}
        response = getattr(client, method)(path, headers=bearer(raw), **kwargs)
        assert response.status_code == 401, path
        assert response.json()["detail"]["code"] == "invalid_token", path


def test_repeated_failed_attempts_from_one_address_are_rate_limited():
    original = rate_limit.failed_auth_limiter
    rate_limit.failed_auth_limiter = SlidingWindowLimiter(max_events=3, window_seconds=60)
    try:
        client = client_for_token_auth([])  # every lookup misses
        headers = bearer(api_tokens.generate_token())
        codes = [client.post("/api/v1/sleep/start", headers=headers).status_code for _ in range(5)]
        assert codes == [401, 401, 401, 429, 429]
        blocked = client.post("/api/v1/sleep/start", headers=headers)
        assert blocked.json()["detail"]["code"] == "rate_limited"
    finally:
        rate_limit.failed_auth_limiter = original


def test_a_single_token_is_rate_limited_per_minute():
    original = rate_limit.token_usage_limiter
    rate_limit.token_usage_limiter = SlidingWindowLimiter(max_events=2, window_seconds=60)
    try:
        row, raw = token_row()
        client = client_for_token_auth([row], [default_user()], [])
        codes = [client.post("/api/v1/sleep/start", headers=bearer(raw)).status_code for _ in range(3)]
        assert codes == [200, 200, 429]
    finally:
        rate_limit.token_usage_limiter = original
