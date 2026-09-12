from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from tshortner.models.url import ShortURL


class URLRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        long_url: str,
        user_id: str,
        short_code: str | None = None,
        expires_at: datetime | None = None,
    ) -> ShortURL:
        entry = ShortURL(short_code=short_code, long_url=long_url, user_id=user_id, expires_at=expires_at)
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return entry

    async def get_by_code(self, short_code: str) -> ShortURL | None:
        result = await self._session.exec(select(ShortURL).where(ShortURL.short_code == short_code))
        return result.first()

    async def get_by_user_and_long_url(self, user_id: str, long_url: str) -> ShortURL | None:
        result = await self._session.exec(
            select(ShortURL).where(ShortURL.user_id == user_id, ShortURL.long_url == long_url)
        )
        return result.first()

    async def update(self, entry: ShortURL) -> ShortURL:
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return entry

    async def increment_click_count(self, short_code: str) -> None:
        entry = await self.get_by_code(short_code)
        if entry is not None:
            entry.click_count += 1
            self._session.add(entry)
            await self._session.commit()
