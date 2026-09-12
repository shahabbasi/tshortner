from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ShortURL(SQLModel, table=True):
    __tablename__ = "short_urls"
    __table_args__ = (UniqueConstraint("user_id", "long_url", name="uq_short_urls_user_id_long_url"),)

    id: int | None = Field(default=None, primary_key=True)
    # Nullable at the DB level (though not in the type) so a newly-inserted row can hold a
    # placeholder before its id-derived short_code is backfilled — Postgres unique indexes
    # treat NULLs as distinct, so concurrent inserts never collide here, unlike "".
    short_code: str = Field(index=True, unique=True, nullable=True, max_length=32)
    # Test-only identifier sent by the client on create; not backed by real auth. A given
    # user gets one short code per long_url (uq_short_urls_user_id_long_url above), but
    # different users each get their own code for the same long_url.
    user_id: str = Field(index=True, nullable=False, max_length=128)
    long_url: str = Field(nullable=False, max_length=2048)
    # timezone=True must match the migration's TIMESTAMP WITH TIME ZONE columns — otherwise
    # asyncpg rejects the timezone-aware datetimes this app writes (_utcnow()).
    created_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
    expires_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    click_count: int = Field(default=0, nullable=False)
