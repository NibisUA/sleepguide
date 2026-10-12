import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fakes import client_for_token_auth
from fastapi import Request

from app.api.deps import client_ip
from app.bot import handlers, texts
from app.bot.setup import set_commands
from app.core import rate_limit
from app.core.config import Settings, get_settings
from app.core.rate_limit import SlidingWindowLimiter


def test_login_requests_are_rate_limited_even_when_initdata_is_invalid(monkeypatch):
    monkeypatch.setattr(rate_limit, "login_limiter", SlidingWindowLimiter(2, 60))
    # auth imports the limiter directly, so override the same instance there.
    from app.api import auth

    monkeypatch.setattr(auth, "login_limiter", rate_limit.login_limiter)
    client = client_for_token_auth()
    codes = [
        client.post("/api/v1/auth/telegram", json={"init_data": "invalid"}).status_code
        for _ in range(4)
    ]
    assert codes == [401, 401, 429, 429]


def test_forwarded_addresses_are_trusted_only_from_the_proxy(monkeypatch):
    monkeypatch.setattr(get_settings(), "trusted_proxy_ips", ["172.30.28.2"])

    def request(peer):
        return Request(
            {"type": "http", "client": (peer, 123), "headers": [(b"x-forwarded-for", b"1.2.3.4")]}
        )

    assert client_ip(request("203.0.113.10")) == "203.0.113.10"
    assert client_ip(request("172.30.28.2")) == "1.2.3.4"


def test_production_settings_refuse_short_secrets_and_dev_login():
    settings = Settings(
        env="prod",
        jwt_secret="x" * 32,
        bot_token="token",
        webhook_secret="y" * 32,
        mini_app_url="https://example.com",
        webhook_base_url="https://example.com",
    )
    settings.validate_for_runtime()
    settings.jwt_secret = "short"
    with pytest.raises(RuntimeError, match="32 bytes"):
        settings.validate_for_runtime()
    settings.jwt_secret = "x" * 32
    settings.dev_login_enabled = True
    with pytest.raises(RuntimeError, match="DEV_LOGIN"):
        settings.validate_for_runtime()


def test_bot_help_and_privacy_work_without_creating_an_account(monkeypatch):
    monkeypatch.setattr(get_settings(), "mini_app_url", "https://example.com")
    message = SimpleNamespace(from_user=SimpleNamespace(language_code="uk-UA"), answer=AsyncMock())
    asyncio.run(handlers.on_help_command(message))
    assert "/privacy" in message.answer.call_args.args[0]
    asyncio.run(handlers.on_privacy_command(message))
    keyboard = message.answer.call_args.kwargs["reply_markup"]
    assert keyboard.inline_keyboard[0][0].url == "https://example.com/privacy/uk"


def test_bot_menu_and_descriptions_are_localized_and_within_limits():
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(),
        set_my_description=AsyncMock(),
        set_my_short_description=AsyncMock(),
    )
    asyncio.run(set_commands(bot))
    assert bot.set_my_commands.call_count == 2
    assert [command.command for command in bot.set_my_commands.call_args.args[0]] == [
        "sleep",
        "wake",
        "help",
        "privacy",
    ]
    for lang in ("uk", "en"):
        assert len(texts.text(lang, "description")) <= 512
        assert len(texts.text(lang, "short_description")) <= 120
