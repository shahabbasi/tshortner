from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from tshortner.api.deps import ShortenerServiceDep
from tshortner.schemas.url import ShortenRequest, ShortenResponse

router = APIRouter()


@router.post("/urls", response_model=ShortenResponse, status_code=201)
async def shorten_url(payload: ShortenRequest, request: Request, service: ShortenerServiceDep) -> ShortenResponse:
    entry = await service.shorten(long_url=str(payload.long_url), user_id=payload.user_id, expires_at=payload.expires_at)
    base_url = str(request.base_url).rstrip("/")
    return ShortenResponse(
        short_code=entry.short_code,
        short_url=f"{base_url}/{entry.short_code}",
        long_url=entry.long_url,
        created_at=entry.created_at,
        expires_at=entry.expires_at,
    )


@router.get("/{short_code}")
async def redirect_to_long_url(short_code: str, service: ShortenerServiceDep) -> RedirectResponse:
    long_url = await service.resolve(short_code)
    if long_url is None:
        raise HTTPException(status_code=404, detail="short URL not found")
    return RedirectResponse(url=long_url, status_code=302)
