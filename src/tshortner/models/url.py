from datetime import datetime, timezone

from sqlalchemy import DateTime, Index
from sqlmodel import Field, SQLModel


class ShortURL(SQLModel, table=True):
    __tablename__ = "short_urls"
    # One code per user per URL; other users still get their own code for the same URL.
    __table_args__ = (Index("ix_short_urls_user_id_original_url", "user_id", "original_url", unique=True),)

    id: int | None = Field(default=None, primary_key=True)
    # NULL once the link expires; its code moves to expired_short_code.
    short_code: str | None = Field(default=None, index=True, unique=True, max_length=32)
    user_id: str = Field(max_length=128)  # test-only identifier, not backed by auth
    original_url: str = Field(max_length=2048)
    # timezone=True keeps these TIMESTAMPTZ; asyncpg rejects aware datetimes bound to naive columns.
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=DateTime(timezone=True))
    expires_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    click_count: int = 0
    expired_short_code: str | None = Field(default=None, index=True, max_length=32)
