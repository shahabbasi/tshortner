from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from tshortner.utils.short_code import ALPHABET


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "tshortner"
    debug: bool = False

    postgres_dsn: str = "postgresql+asyncpg://tshortner:tshortner@localhost:5432/tshortner"
    redis_dsn: str = "redis://localhost:6379/0"

    short_code_length: int = Field(default=7, ge=2, le=32)
    # First characters this instance's codes may start with, e.g. SHORT_CODE_PREFIXES=a,b,c.
    # Give each instance a disjoint set and they can never generate the same code.
    short_code_prefixes: Annotated[list[str], NoDecode] = list(ALPHABET)

    cache_ttl_seconds: int = 300
    access_events_channel: str = "tshortner:access_events"
    access_log_flush_interval_seconds: float = 60.0
    expiry_check_interval_seconds: float = 3600.0

    @field_validator("short_code_prefixes", mode="before")
    @classmethod
    def _split_prefixes(cls, value: object) -> object:
        return [prefix.strip() for prefix in value.split(",") if prefix.strip()] if isinstance(value, str) else value

    @field_validator("short_code_prefixes")
    @classmethod
    def _check_prefixes(cls, prefixes: list[str]) -> list[str]:
        if not prefixes or len(set(prefixes)) != len(prefixes) or any(len(p) != 1 or p not in ALPHABET for p in prefixes):
            raise ValueError(f"must be distinct single characters from {ALPHABET}")
        return prefixes


@lru_cache
def get_settings() -> Settings:
    return Settings()
