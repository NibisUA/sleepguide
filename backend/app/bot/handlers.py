"""Bot handlers for quick sleep actions: inline buttons from reminders and /sleep, /wake."""

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from app.bot import actions, texts
from app.core.config import get_settings

router = Router()


def open_app_keyboard(lang: str) -> InlineKeyboardMarkup | None:
    url = get_settings().mini_app_url
    if not url:
        return None
    button = InlineKeyboardButton(text=texts.text(lang, "open_app"), web_app=WebAppInfo(url=url))
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


async def _finish_callback(callback: CallbackQuery, outcome: actions.Outcome) -> None:
    """Acknowledge the tap and replace the reminder (and its button) with the result."""
    await callback.answer()
    message = callback.message
    if not isinstance(message, Message):  # inaccessible (too old) message
        return
    keyboard = open_app_keyboard(outcome.language) if outcome.open_app else None
    try:
        await message.edit_text(outcome.text, reply_markup=keyboard)
    except TelegramBadRequest:  # e.g. "message is not modified"
        pass


@router.callback_query(F.data == actions.CB_START)
async def on_start_button(callback: CallbackQuery) -> None:
    outcome = await actions.start_sleep(callback.from_user.id, callback.from_user.language_code)
    await _finish_callback(callback, outcome)


@router.callback_query(F.data == actions.CB_STOP)
async def on_stop_button(callback: CallbackQuery) -> None:
    outcome = await actions.stop_sleep(callback.from_user.id, callback.from_user.language_code)
    await _finish_callback(callback, outcome)


@router.message(Command("sleep"))
async def on_sleep_command(message: Message) -> None:
    if message.from_user is None:
        return
    outcome = await actions.start_sleep(message.from_user.id, message.from_user.language_code)
    await message.answer(outcome.text)


@router.message(Command("wake"))
async def on_wake_command(message: Message) -> None:
    if message.from_user is None:
        return
    outcome = await actions.stop_sleep(message.from_user.id, message.from_user.language_code)
    keyboard = open_app_keyboard(outcome.language) if outcome.open_app else None
    await message.answer(outcome.text, reply_markup=keyboard)


@router.message(Command("help"))
async def on_help_command(message: Message) -> None:
    lang = texts.lang_of(message.from_user.language_code if message.from_user else None)
    await message.answer(texts.text(lang, "help"), reply_markup=open_app_keyboard(lang))


@router.message(Command("privacy"))
async def on_privacy_command(message: Message) -> None:
    lang = texts.lang_of(message.from_user.language_code if message.from_user else None)
    base = get_settings().mini_app_url.rstrip("/")
    keyboard = (
        InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=texts.text(lang, "privacy_button"), url=f"{base}/privacy/{lang}"
                    )
                ]
            ]
        )
        if base
        else None
    )
    await message.answer(texts.text(lang, "privacy"), reply_markup=keyboard)
