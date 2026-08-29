import os
from typing import List, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    DATABASE_URL: str = "sqlite+aiosqlite:///./quizbot.db"
    ADMIN_IDS_RAW: str = Field(default="", alias="ADMIN_IDS")
    DEFAULT_MIN_INTERVAL: int = 10
    DEFAULT_MAX_INTERVAL: int = 10
    DEFAULT_QUIZ_DURATION: int = 10
    LOG_LEVEL: str = "INFO"
    DEFAULT_LANGUAGE: str = "en"
    WEBHOOK_URL: str = ""
    WEBHOOK_SECRET: str = ""
    CRON_SECRET: str = ""

    @field_validator("DEFAULT_MIN_INTERVAL", "DEFAULT_MAX_INTERVAL", "DEFAULT_QUIZ_DURATION", mode="before")
    @classmethod
    def parse_empty_int(cls, v: Any, info) -> int:
        if v is None or v == "" or (isinstance(v, str) and not v.strip()):
            return 10
        try:
            return int(v)
        except Exception:
            return 10

    @field_validator("BOT_TOKEN", "DATABASE_URL", "WEBHOOK_URL", "WEBHOOK_SECRET", "CRON_SECRET", mode="before")
    @classmethod
    def strip_strings(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip()
        return str(v) if v is not None else ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


    @property
    def ASYNC_DATABASE_URL(self) -> str:
        url = (self.DATABASE_URL or "").strip()
        if os.environ.get("VERCEL") and "sqlite" in url:
            # On Vercel serverless, root filesystem is read-only. Fallback to /tmp.
            return "sqlite+aiosqlite:////tmp/quizbot.db"
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # asyncpg does not accept sslmode= query param; it expects ssl=
        if "sslmode=" in url:
            url = url.replace("sslmode=", "ssl=")
        return url

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
