from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ShellBot"
    app_base_url: str = "http://127.0.0.1:8088"
    database_url: str = "sqlite:///./shellbot.db"
    tenants_file: str = "config/tenants.example.json"

    meta_verify_token: str = "change-me"
    meta_access_token: str = ""
    meta_api_version: str = "v20.0"
    shellbot_dry_run: bool = True

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "shellbot@example.com"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()

