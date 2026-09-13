from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from tshortner.api.access_recording import record_short_link_access
from tshortner.api.deps import ShortenerServiceDep
from tshortner.schemas.url import OpenCountResponse, ShortenRequest, ShortenResponse
from tshortner.services.shortener import ShortenInProgressError

router = APIRouter()


@router.post("/urls", status_code=201)
async def shorten_url(payload: ShortenRequest, request: Request, service: ShortenerServiceDep) -> ShortenResponse:
    try:
        entry = await service.shorten(str(payload.original_url), payload.user_id, payload.expires_at)
    except ShortenInProgressError:
        raise HTTPException(
            status_code=409,
            detail="Another request is still shortening this URL. Retry in a moment.",
            headers={"Retry-After": "1"},
        )
    short_url = str(request.url_for("redirect_to_original_url", short_code=entry.short_code))
    return ShortenResponse(**entry.model_dump(), short_url=short_url)


@router.get("/urls/{short_url_id}/stats")
async def get_open_count(short_url_id: int, service: ShortenerServiceDep) -> OpenCountResponse:
    open_count = await service.get_open_count(short_url_id)
    if open_count is None:
        raise HTTPException(status_code=404, detail="short url not found")
    return OpenCountResponse(short_url_id=short_url_id, open_count=open_count)


@router.get("/{short_code}")
@record_short_link_access
async def redirect_to_original_url(short_code: str, service: ShortenerServiceDep) -> RedirectResponse:
    original_url = await service.resolve(short_code)
    if original_url is None:
        raise HTTPException(status_code=404, detail="short URL not found")
    return RedirectResponse(original_url, status_code=302)
