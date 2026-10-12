from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ApiToken,
    Exercise,
    ExerciseLog,
    Insight,
    ScreenTimeDaily,
    SleepFeedback,
    SleepSession,
    StressLog,
    User,
    Workout,
)
from app.schemas.exercise import ExerciseLogOut, ExerciseOut
from app.schemas.insight import InsightOut
from app.schemas.personal import FeedbackExportOut
from app.schemas.privacy import (
    DataExportOut,
    ScreenExportOut,
    SleepExportOut,
    StressExportOut,
    TokenExportOut,
    UserExportOut,
    WorkoutExportOut,
)


async def export_data(session: AsyncSession, user: User) -> DataExportOut:
    # Only this user's rows; all dates, including open sessions and revoked tokens.
    # Authentication secrets, token hashes and server credentials never leave the server.
    rows = {}
    for name, model, schema in (
        ("sleep_sessions", SleepSession, SleepExportOut),
        ("workouts", Workout, WorkoutExportOut),
        ("stress_logs", StressLog, StressExportOut),
        ("screen_time", ScreenTimeDaily, ScreenExportOut),
        ("api_tokens", ApiToken, TokenExportOut),
        ("insights", Insight, InsightOut),
        ("exercises", Exercise, ExerciseOut),
        ("exercise_logs", ExerciseLog, ExerciseLogOut),
        ("sleep_feedback", SleepFeedback, FeedbackExportOut),
    ):
        result = await session.execute(
            select(model).where(model.user_id == user.id).order_by(model.id)
        )
        rows[name] = [schema.model_validate(row) for row in result.scalars()]
    return DataExportOut(
        exported_at=datetime.now(UTC), user=UserExportOut.model_validate(user), **rows
    )


async def delete_account(session: AsyncSession, user: User) -> None:
    # Every child FK has ON DELETE CASCADE, including tokens and insights.
    # JWTs resolve the user on each request, so deletion also invalidates old sessions.
    await session.delete(user)
    await session.commit()
