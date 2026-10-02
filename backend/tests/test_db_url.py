from app.core.db_url import normalize_database_url as n


def test_neon_url_is_converted():
    url = "postgresql://user:pw@ep-x.neon.tech/db?sslmode=require&channel_binding=require"
    assert n(url) == "postgresql+asyncpg://user:pw@ep-x.neon.tech/db?ssl=require"


def test_postgres_scheme_is_converted():
    assert n("postgres://u:p@h:5432/d") == "postgresql+asyncpg://u:p@h:5432/d"


def test_already_asyncpg_url_is_unchanged():
    url = "postgresql+asyncpg://u:p@localhost:5432/d"
    assert n(url) == url
