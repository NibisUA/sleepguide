"""Personal API tokens: generation and hashing (stdlib only).

A token is a long random secret shown to the user exactly once; only its SHA-256 digest is stored.
Plain SHA-256 is appropriate because the secret has 256 bits of entropy (it cannot be guessed or
brute-forced like a password).
"""

import hashlib
import hmac
import secrets

TOKEN_PREFIX = "sg_"
HINT_LENGTH = 8  # "sg_" + 5 characters: enough to recognize a token in a list, useless to attack


def generate_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def looks_like_api_token(value: str) -> bool:
    return value.startswith(TOKEN_PREFIX)


def token_hint(raw: str) -> str:
    return raw[:HINT_LENGTH]


def digests_match(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
