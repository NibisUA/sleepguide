"""Compare a quiet source DB with a disposable restored DB. Credentials stay in env.

RESTORE_SOURCE_URL / RESTORE_TARGET_URL; target DB must end in _test.
Outputs counts and equality only, never rows or connection strings.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.models import Base  # noqa: E402


async def main():
    source_url = os.environ["RESTORE_SOURCE_URL"]
    target_url = os.environ["RESTORE_TARGET_URL"]
    if not (make_url(target_url).database or "").endswith("_test"):
        raise RuntimeError("Restore comparison target must be a disposable *_test database")
    engines = [create_async_engine(url) for url in (source_url, target_url)]
    try:
        async with engines[0].connect() as source, engines[1].connect() as target:
            for table in Base.metadata.sorted_tables:
                statement = select(table).order_by(table.c.id)
                left = [dict(row) for row in (await source.execute(statement)).mappings()]
                right = [dict(row) for row in (await target.execute(statement)).mappings()]
                if left != right:
                    raise RuntimeError(f"Restored data mismatch: {table.name}")
                print(json.dumps({"table": table.name, "rows": len(left), "equal": True}))
            revisions = [
                await connection.scalar(text("SELECT version_num FROM alembic_version"))
                for connection in (source, target)
            ]
            assert revisions[0] == revisions[1], "Migration revision differs"
        print("All restored rows and migration revision match")
    finally:
        for engine in engines:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
