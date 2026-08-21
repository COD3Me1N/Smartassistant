from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    ultramsg_instance_id: str = "instanceXXXX"
    ultramsg_token: str = "your_token"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    database_url: str = "sqlite+aiosqlite:///./smart_assistant.db"
    dashboard_secret: str = "change-me"
    admin_password: str = "admin123"
    meta_access_token: str = ""
    meta_ad_account_id: str = ""
    meta_app_id: str = ""
    meta_app_secret: str = ""
    app_url: str = "http://localhost:8000"
    company_name: str = "Smart Assistant"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
