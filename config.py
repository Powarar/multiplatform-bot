from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: list[int] = []
    DATABASE_URL: str = "sqlite+aiosqlite:///./multi_platform_bot.db"

    @field_validator('ADMIN_IDS', mode='before')
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(id.strip()) for id in v.split(',') if id.strip()]
        elif isinstance(v, int):
            return [v]
        return v


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
