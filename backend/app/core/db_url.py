"""Normalize a PostgreSQL URL (as given by Neon/Render/Supabase) for SQLAlchemy + asyncpg."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def normalize_database_url(url: str) -> str:
    # postgres:// and postgresql:// -> postgresql+asyncpg://
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url[len(prefix):]
            break

    parts = urlsplit(url)
    query: list[tuple[str, str]] = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key == "channel_binding":  # added by Neon, not supported by asyncpg
            continue
        if key == "sslmode":  # libpq name -> asyncpg name
            key = "ssl"
        query.append((key, value))
    return urlunsplit(parts._replace(query=urlencode(query)))
