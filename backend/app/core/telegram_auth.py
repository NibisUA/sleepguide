"""Server-side validation of Telegram Mini App `initData`. Stdlib only."""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class InitDataError(Exception):
    """Raised when initData is missing, tampered with or too old."""


@dataclass(frozen=True)
class TelegramUser:
    id: int
    language_code: str | None


def validate_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int,
    now: float | None = None,
) -> TelegramUser:
    if not init_data or not bot_token:
        raise InitDataError("missing_init_data")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("missing_hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise InitDataError("bad_signature")

    try:
        auth_date = int(pairs["auth_date"])
    except (KeyError, ValueError):
        raise InitDataError("bad_auth_date") from None
    current = time.time() if now is None else now
    if current - auth_date > max_age_seconds or auth_date - current > 60:
        raise InitDataError("expired")

    try:
        user = json.loads(pairs["user"])
        return TelegramUser(id=int(user["id"]), language_code=user.get("language_code"))
    except (KeyError, ValueError, TypeError):
        raise InitDataError("bad_user") from None
