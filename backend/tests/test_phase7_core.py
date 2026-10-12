from datetime import date, timedelta

from app.analytics import screen_time_rules as r
from app.core import api_tokens
from app.core.rate_limit import SlidingWindowLimiter

# ---------- API token helpers ----------


def test_token_format_and_uniqueness():
    first, second = api_tokens.generate_token(), api_tokens.generate_token()
    assert first.startswith("sg_") and second.startswith("sg_")
    assert first != second
    assert len(first) >= 40  # 256 bits of randomness, url-safe
    assert api_tokens.looks_like_api_token(first)
    assert not api_tokens.looks_like_api_token("eyJhbGciOiJIUzI1NiJ9.payload.signature")  # a JWT


def test_only_the_digest_is_stored_and_it_is_stable():
    raw = api_tokens.generate_token()
    digest = api_tokens.hash_token(raw)
    assert len(digest) == 64 and digest != raw and raw not in digest
    assert api_tokens.hash_token(raw) == digest
    assert api_tokens.hash_token(raw + "x") != digest
    assert api_tokens.digests_match(digest, api_tokens.hash_token(raw))
    assert not api_tokens.digests_match(digest, api_tokens.hash_token("other"))


def test_hint_is_short_and_does_not_reveal_the_secret():
    raw = api_tokens.generate_token()
    hint = api_tokens.token_hint(raw)
    assert hint == raw[:8] and len(hint) == 8 and len(raw) > 4 * len(hint)


# ---------- rate limiter ----------


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_limiter_blocks_after_the_limit_and_recovers_when_the_window_passes():
    clock = Clock()
    limiter = SlidingWindowLimiter(max_events=3, window_seconds=60, clock=clock)
    assert [limiter.allow("ip") for _ in range(4)] == [True, True, True, False]
    assert limiter.is_blocked("ip")
    clock.now += 61
    assert not limiter.is_blocked("ip")
    assert limiter.allow("ip")


def test_limiter_keys_are_independent_and_hits_alone_can_block():
    limiter = SlidingWindowLimiter(max_events=2, window_seconds=60, clock=Clock())
    limiter.hit("a")
    limiter.hit("a")
    assert limiter.is_blocked("a")
    assert not limiter.is_blocked("b")


def test_limiter_is_a_sliding_window():
    clock = Clock()
    limiter = SlidingWindowLimiter(max_events=2, window_seconds=60, clock=clock)
    limiter.hit("k")
    clock.now += 40
    limiter.hit("k")
    clock.now += 30  # the first hit (70 s ago) has expired, the second (30 s ago) has not
    assert not limiter.is_blocked("k")
    limiter.hit("k")
    assert limiter.is_blocked("k")


# ---------- Screen Time rules ----------


def test_usage_validation():
    assert r.is_valid_usage(0, None)
    assert r.is_valid_usage(318, 34)
    assert r.is_valid_usage(1440, 120)
    assert not r.is_valid_usage(1441, None)
    assert not r.is_valid_usage(-1, None)
    assert not r.is_valid_usage(300, 121)  # more than the 2-hour pre-bed window
    assert not r.is_valid_usage(30, 45)  # pre-bed usage cannot exceed the daily total
    assert r.is_valid_usage(30, 30)
    assert not r.is_valid_usage(300, -5)


def test_date_range():
    today = date(2026, 10, 5)
    assert r.is_date_in_range(today, today)
    assert r.is_date_in_range(today - timedelta(days=365), today)
    assert not r.is_date_in_range(today - timedelta(days=366), today)
    assert not r.is_date_in_range(today + timedelta(days=1), today)
