from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "tshortner"
    debug: bool = False

    postgres_dsn: str = "postgresql+asyncpg://tshortner:tshortner@localhost:5432/tshortner"
    redis_dsn: str = "redis://localhost:6379/0"

    short_code_length: int = 7
    cache_ttl_seconds: int = 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()
