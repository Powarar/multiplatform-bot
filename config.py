from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    BOT_TOKEN: str
    ADMIN_IDS: list[int] = []
    DATABASE_URL: str = "sqlite+aiosqlite:///./multi_platform_bot.db"

    VK_API_VERSION: str = "5.131"

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, int):
            return [v]
        return v


settings = Settings()
BOT_TOKEN = settings.BOT_TOKEN
ADMIN_IDS = settings.ADMIN_IDS
DATABASE_URL = settings.DATABASE_URL
