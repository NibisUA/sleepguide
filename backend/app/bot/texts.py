"""Bot messages (uk / en). Kept in one place so wording is easy to review."""

TEXTS: dict[str, dict[str, str]] = {
    "uk": {
        "evening": "🌙 Час готуватися до сну. Натисни кнопку, коли ляжеш.",
        "evening_button": "🌙 Почати сон",
        "morning": "☀️ Доброго ранку! Сон ще триває. Натисни, коли прокинешся.",
        "morning_button": "☀️ Я прокинувся",
        "started": "🌙 Добраніч! Сон розпочато о {time}.",
        "already": "🌙 Сон уже триває з {time}.",
        "stopped": "☀️ Доброго ранку! Ти спав {duration}.",
        "stopped_score": "☀️ Доброго ранку! Ти спав {duration}. Sleep Score: {score}.",
        "nap": "😴 Денний сон збережено: {duration}.",
        "no_open": "Зараз немає активного сну. Надішли /sleep, коли ляжеш.",
        "confirm_in_app": "Сон триває понад 14 годин. Відкрий застосунок і вкажи, коли ти прокинувся.",
        "open_app": "Відкрити SleepGuide",
        "duration_hm": "{h} год {m} хв",
        "duration_m": "{m} хв",
        "cmd_sleep": "Почати сон",
        "cmd_wake": "Я прокинувся",
    },
    "en": {
        "evening": "🌙 Time to wind down. Tap the button when you go to bed.",
        "evening_button": "🌙 Start sleep",
        "morning": "☀️ Good morning! Your sleep is still running. Tap when you wake up.",
        "morning_button": "☀️ I woke up",
        "started": "🌙 Good night! Sleep started at {time}.",
        "already": "🌙 Sleep has been running since {time}.",
        "stopped": "☀️ Good morning! You slept {duration}.",
        "stopped_score": "☀️ Good morning! You slept {duration}. Sleep Score: {score}.",
        "nap": "😴 Nap saved: {duration}.",
        "no_open": "There is no sleep in progress. Send /sleep when you go to bed.",
        "confirm_in_app": "This sleep has been running for over 14 hours. Open the app and tell us when you woke up.",
        "open_app": "Open SleepGuide",
        "duration_hm": "{h}h {m}m",
        "duration_m": "{m}m",
        "cmd_sleep": "Start sleep",
        "cmd_wake": "I woke up",
    },
}


def lang_of(code: str | None) -> str:
    return "uk" if code == "uk" else "en"


def text(lang: str, key: str, **kwargs: object) -> str:
    return TEXTS[lang_of(lang)][key].format(**kwargs)


def duration(lang: str, minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    if hours:
        return text(lang, "duration_hm", h=hours, m=mins)
    return text(lang, "duration_m", m=mins)
