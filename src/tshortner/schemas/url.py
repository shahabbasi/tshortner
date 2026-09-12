from datetime import datetime

from pydantic import BaseModel, HttpUrl


class ShortenRequest(BaseModel):
    long_url: HttpUrl
    # Test-only identifier: not backed by real auth, used to scope per-user dedup.
    user_id: str
    expires_at: datetime | None = None


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    long_url: str
    created_at: datetime
    expires_at: datetime | None = None


class URLStatsResponse(BaseModel):
    short_code: str
    long_url: str
    created_at: datetime
    expires_at: datetime | None = None
    click_count: int
