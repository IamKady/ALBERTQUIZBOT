import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    DATABASE_URL: str = "sqlite+aiosqlite:///./quizbot.db"
    ADMIN_IDS_RAW: str = Field(default="", alias="ADMIN_IDS")
    DEFAULT_MIN_INTERVAL: int = 10
    DEFAULT_MAX_INTERVAL: int = 10
    DEFAULT_QUIZ_DURATION: int = 10
    LOG_LEVEL: str = "INFO"
    DEFAULT_LANGUAGE: str = "en"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def ADMIN_IDS(self) -> List[int]:
        raw = self.ADMIN_IDS_RAW
        if not raw:
            return []
        ids = []
        for item in str(raw).split(","):
            item = item.strip()
            if item.isdigit():
                ids.append(int(item))
        return ids

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.ADMIN_IDS

settings = Settings()
