import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.core.telegram_auth import InitDataError, validate_init_data

BOT_TOKEN = "123456:TEST-TOKEN"


def make_init_data(user_id=42, auth_date=None, token=BOT_TOKEN, tamper=False):
    fields = {
        "auth_date": str(int(time.time()) if auth_date is None else auth_date),
        "query_id": "AAH-test",
        "user": json.dumps({"id": user_id, "first_name": "T", "language_code": "uk"}),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    if tamper:
        fields["user"] = json.dumps({"id": 1, "first_name": "Evil"})
    return urlencode(fields)


def test_valid_init_data():
    user = validate_init_data(make_init_data(user_id=42), BOT_TOKEN, 3600)
    assert user.id == 42
    assert user.language_code == "uk"


def test_tampered_payload_is_rejected():
    with pytest.raises(InitDataError):
        validate_init_data(make_init_data(tamper=True), BOT_TOKEN, 3600)


def test_wrong_bot_token_is_rejected():
    with pytest.raises(InitDataError):
        validate_init_data(make_init_data(token="other:token"), BOT_TOKEN, 3600)


def test_expired_init_data_is_rejected():
    old = int(time.time()) - 7200
    with pytest.raises(InitDataError):
        validate_init_data(make_init_data(auth_date=old), BOT_TOKEN, 3600)


def test_missing_hash_is_rejected():
    with pytest.raises(InitDataError):
        validate_init_data("auth_date=1&user=%7B%7D", BOT_TOKEN, 3600)


def test_empty_input_is_rejected():
    with pytest.raises(InitDataError):
        validate_init_data("", BOT_TOKEN, 3600)
