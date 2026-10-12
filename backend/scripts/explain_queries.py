"""Record actual PostgreSQL plans for the bounded history queries. No row data.

EXPLAIN_USER_ID selects a demo/test user. Connection comes from DATABASE_URL.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text  # noqa: E402

from app.core.db import engine  # noqa: E402


async def main():
    user_id = int(os.environ["EXPLAIN_USER_ID"])
    async with engine.connect() as connection:
        for table in ("sleep_sessions", "workouts", "stress_logs", "screen_time_daily"):
            print(f"=== {table}: bounded per-user history ===")
            # Table names are a fixed allowlist; user ID is bound, not interpolated.
            result = await connection.execute(
                text(
                    f"EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM {table} "
                    "WHERE user_id = :user_id AND local_date BETWEEN CURRENT_DATE - 180 AND CURRENT_DATE"
                ),
                {"user_id": user_id},
            )
            for row in result:
                print(row[0])
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
