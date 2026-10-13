import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.bot.reminders import run_reminder_loop
from app.bot.setup import create_bot, create_dispatcher, set_commands
from app.bot.webhook import build_webhook_router
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services.errors import DomainError

ERROR_STATUS = {
    "no_open_session": 404,
    "sleep_not_found": 404,
    "wake_time_required": 409,
    "overlap": 409,
    "invalid_time": 422,
    "too_long": 422,
    "invalid_range": 422,
    "invalid_cursor": 422,
    "workout_not_found": 404,
    "no_running_workout": 404,
    "end_time_required": 409,
    "stress_not_found": 404,
    "invalid_date": 422,
    "invalid_screen_time": 422,
    "invalid_screen_categories": 422,
    "screen_time_not_found": 404,
    "too_many_tokens": 409,
    "api_token_not_found": 404,
    "rate_limited": 429,
    "exercise_not_found": 404,
    "exercise_log_not_found": 404,
    "exercise_exists": 409,
    "exercise_limit": 409,
    "exercise_log_limit": 409,
    "workout_unfinished": 409,
    "exercise_metrics": 422,
    "exercise_time": 422,
}


def create_app() -> FastAPI:
    settings = get_settings()
    bot = create_bot(settings.bot_token) if settings.bot_token else None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        settings.validate_for_runtime()
        if bot and settings.webhook_base_url and settings.webhook_secret:
            try:
                await bot.set_webhook(
                    f"{settings.webhook_base_url.rstrip('/')}/telegram/webhook",
                    secret_token=settings.webhook_secret,
                    allowed_updates=["message", "callback_query"],
                )
            except Exception:  # the API must still start if Telegram is unreachable
                logging.getLogger(__name__).exception("Failed to set Telegram webhook")
        if bot:
            try:
                await set_commands(bot)
            except Exception:
                logging.getLogger(__name__).exception("Failed to set bot commands")
        # One process, one loop (see app/bot/reminders.py). Do not run several workers.
        reminder_task = (
            asyncio.create_task(run_reminder_loop(bot))
            if bot and settings.reminders_enabled
            else None
        )
        yield
        if reminder_task:
            reminder_task.cancel()
            with suppress(asyncio.CancelledError):
                await reminder_task
        if bot:
            await bot.session.close()

    app = FastAPI(title="SleepGuide API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=ERROR_STATUS.get(exc.code, 400),
            content={"detail": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Never echo user input (which could be initData or a token) into an error.
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "validation_error",
                    "message": "Check the submitted values",
                }
            },
        )

    @app.middleware("http")
    async def response_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health", include_in_schema=False)
    async def health() -> JSONResponse:
        try:
            async with asyncio.timeout(3):
                async with SessionLocal() as session:
                    await session.execute(text("SELECT 1"))
        except (SQLAlchemyError, OSError, TimeoutError):
            return JSONResponse(
                status_code=503,
                content={"status": "error", "database": "unavailable"},
                headers={"Cache-Control": "no-store"},
            )
        return JSONResponse(
            content={"status": "ok", "database": "ok"}, headers={"Cache-Control": "no-store"}
        )

    app.include_router(api_router)
    if bot and settings.webhook_secret:
        app.include_router(build_webhook_router(bot, create_dispatcher(), settings.webhook_secret))
    return app


app = create_app()
