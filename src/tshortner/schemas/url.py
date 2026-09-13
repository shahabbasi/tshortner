from datetime import datetime

from pydantic import BaseModel, HttpUrl


class ShortenRequest(BaseModel):
    original_url: HttpUrl
    # Test-only identifier: not backed by real auth, used to scope per-user dedup.
    user_id: str
    expires_at: datetime | None = None


class ShortenResponse(BaseModel):
    id: int
    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: datetime | None = None


class OpenCountResponse(BaseModel):
    short_url_id: int
    open_count: int
