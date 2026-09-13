from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


class AccessLog(SQLModel, table=True):
    __tablename__ = "access_logs"

    id: int | None = Field(default=None, primary_key=True)
    short_url_id: int = Field(foreign_key="short_urls.id", index=True)
    ip_address: str = Field(max_length=45)
    accessed_at: datetime = Field(sa_type=DateTime(timezone=True))
