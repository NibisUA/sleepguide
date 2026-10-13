from fastapi import APIRouter

from app.api import (
    auth,
    csv_data,
    days,
    exercises,
    history,
    insights,
    me,
    personal,
    progress,
    screen_time,
    sleep,
    stress,
    tokens,
    workout,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(sleep.router)
api_router.include_router(workout.router)
api_router.include_router(stress.router)
api_router.include_router(screen_time.router)
api_router.include_router(tokens.router)
api_router.include_router(days.router)
api_router.include_router(insights.router)
api_router.include_router(exercises.router)
api_router.include_router(progress.router)
api_router.include_router(history.router)
api_router.include_router(personal.router)
api_router.include_router(csv_data.router)
