import json
import os
from typing import Dict, Any, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from bot.config.settings import settings

class I18nMiddleware(BaseMiddleware):
    def __init__(self, languages_dir: str = "bot/languages"):
        self.languages_dir = languages_dir
        self.translations: Dict[str, Dict[str, str]] = {}
        self.load_translations()

    def load_translations(self):
        if not os.path.exists(self.languages_dir):
            return
        for file in os.listdir(self.languages_dir):
            if file.endswith(".json"):
                lang_code = file.split(".")[0]
                with open(os.path.join(self.languages_dir, file), "r", encoding="utf-8") as f:
                    self.translations[lang_code] = json.load(f)

    def get_text(self, lang: str, key: str, **kwargs) -> str:
        lang_dict = self.translations.get(lang, self.translations.get(settings.DEFAULT_LANGUAGE, {}))
        text = lang_dict.get(key, self.translations.get("en", {}).get(key, key))
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception:
                pass
        return text

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get("event_from_user")
        lang = user.language_code if user and user.language_code in self.translations else settings.DEFAULT_LANGUAGE
        data["i18n"] = lambda key, **kw: self.get_text(lang, key, **kw)
        return await handler(event, data)
