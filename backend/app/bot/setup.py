from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from app.bot import handlers, texts
from app.core.config import get_settings

router = Router()

TEXTS = {
    "uk": ("Вітаю в SleepGuide! Відстежуй сон, тренування та стрес.", "🌙 Відкрити SleepGuide"),
    "en": ("Welcome to SleepGuide! Track your sleep, workouts and stress.", "🌙 Open SleepGuide"),
}


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    lang = (
        "uk"
        if (message.from_user and (message.from_user.language_code or "").startswith("uk"))
        else "en"
    )
    text, button = TEXTS[lang]
    url = get_settings().mini_app_url
    if not url:
        await message.answer(text)
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=button, web_app=WebAppInfo(url=url))]]
    )
    await message.answer(text, reply_markup=keyboard)


def create_bot(token: str) -> Bot:
    return Bot(token=token)


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    dispatcher.include_router(handlers.router)
    return dispatcher


async def set_commands(bot: Bot) -> None:
    """Set the command menu and descriptions in English and Ukrainian."""
    for language_code, lang in ((None, "en"), ("uk", "uk")):
        commands = [
            BotCommand(command="sleep", description=texts.text(lang, "cmd_sleep")),
            BotCommand(command="wake", description=texts.text(lang, "cmd_wake")),
            BotCommand(command="help", description=texts.text(lang, "cmd_help")),
            BotCommand(command="privacy", description=texts.text(lang, "cmd_privacy")),
        ]
        await bot.set_my_commands(commands, language_code=language_code)
        await bot.set_my_description(
            description=texts.text(lang, "description"), language_code=language_code
        )
        await bot.set_my_short_description(
            short_description=texts.text(lang, "short_description"), language_code=language_code
        )
