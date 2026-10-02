import hmac

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, Header, HTTPException, Request, status


def build_webhook_router(bot: Bot, dispatcher: Dispatcher, secret: str) -> APIRouter:
    router = APIRouter()

    @router.post("/telegram/webhook", include_in_schema=False)
    async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: str | None = Header(default=None),
    ) -> dict[str, bool]:
        if not x_telegram_bot_api_secret_token or not hmac.compare_digest(
            x_telegram_bot_api_secret_token, secret
        ):
            raise HTTPException(status.HTTP_403_FORBIDDEN)
        update = Update.model_validate(await request.json(), context={"bot": bot})
        await dispatcher.feed_update(bot, update)
        return {"ok": True}

    return router
