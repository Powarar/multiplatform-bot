from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8") 
    
    BOT_TOKEN: str
    ADMIN_IDS: list[int] = []
    DATABASE_URL: str = "sqlite+aiosqlite:///./multi_platform_bot.db"
    VK_APP_ID: int
    VK_REDIRECT_URI: str = "https://oauth.vk.com/blank.html"

    @field_validator('ADMIN_IDS', mode='before')
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(id.strip()) for id in v.split(',') if id.strip()]
        elif isinstance(v, int):
            return [v]
        return v



settings = Settings()
