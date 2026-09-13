from collections.abc import Iterable, Mapping
from datetime import datetime

from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from tshortner.models.url import ShortURL


class URLRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, short_code: str, original_url: str, user_id: str, expires_at: datetime | None = None
    ) -> ShortURL:
        entry = ShortURL(short_code=short_code, original_url=original_url, user_id=user_id, expires_at=expires_at)
        self._session.add(entry)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise
        return entry

    async def code_exists(self, short_code: str) -> bool:
        """Checks expired codes too, so a new link never takes over an expired link's code."""
        query = select(ShortURL.id).where(
            or_(ShortURL.short_code == short_code, ShortURL.expired_short_code == short_code)
        )
        return (await self._session.exec(query)).first() is not None

    async def get_by_id(self, short_url_id: int) -> ShortURL | None:
        return await self._session.get(ShortURL, short_url_id)

    async def get_by_code(self, short_code: str) -> ShortURL | None:
        return (await self._session.exec(select(ShortURL).where(ShortURL.short_code == short_code))).first()

    async def get_by_user_and_original_url(self, user_id: str, original_url: str) -> ShortURL | None:
        query = select(ShortURL).where(ShortURL.user_id == user_id, ShortURL.original_url == original_url)
        return (await self._session.exec(query)).first()

    async def get_ids_by_short_codes(self, short_codes: Iterable[str]) -> dict[str, int]:
        query = select(ShortURL.short_code, ShortURL.id).where(ShortURL.short_code.in_(list(short_codes)))
        return dict((await self._session.exec(query)).all())

    async def increment_click_counts(self, counts: Mapping[str, int]) -> None:
        for short_code, count in counts.items():
            await self._session.exec(
                update(ShortURL).where(ShortURL.short_code == short_code).values(click_count=ShortURL.click_count + count)
            )

    async def archive_expired(self, now: datetime) -> list[str]:
        """Moves expired short codes to expired_short_code, keeping the rows; returns the moved codes."""
        result = await self._session.exec(
            update(ShortURL)
            .where(ShortURL.expires_at < now, ShortURL.short_code.is_not(None))
            .values(expired_short_code=ShortURL.short_code, short_code=None)
            # The default session sync re-evaluates the WHERE in Python and crashes comparing
            # expires_at (naive after a SQLite round-trip) with the aware `now`. Nothing needs it.
            .execution_options(synchronize_session=False)
            # RETURNING sees post-update values, so read the moved code, not the now-NULL short_code.
            .returning(ShortURL.expired_short_code)
        )
        return list(result.scalars())
