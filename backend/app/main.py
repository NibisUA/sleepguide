import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.bot.reminders import run_reminder_loop
from app.bot.setup import create_bot, create_dispatcher, set_commands
from app.bot.webhook import build_webhook_router
from app.core.config import get_settings
from app.services.errors import DomainError

ERROR_STATUS = {
    "no_open_session": 404,
    "sleep_not_found": 404,
    "wake_time_required": 409,
    "overlap": 409,
    "invalid_time": 422,
    "too_long": 422,
    "invalid_range": 422,
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
            asyncio.create_task(run_reminder_loop(bot)) if bot and settings.reminders_enabled else None
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

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router)
    if bot and settings.webhook_secret:
        app.include_router(build_webhook_router(bot, create_dispatcher(), settings.webhook_secret))
    return app


app = create_app()
