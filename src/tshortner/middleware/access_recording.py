import json
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from tshortner.core.config import get_settings


async def record_short_link_access(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Publishes an access event per successful short-link redirect; AccessLogWorker persists them."""
    response = await call_next(request)
    # Routing has run by now, so path_params holds the matched route's short_code.
    short_code = request.path_params.get("short_code")
    if short_code is not None and response.status_code == 302:
        event = {
            "short_code": short_code,
            "ip_address": request.client.host if request.client else "unknown",
            "accessed_at": datetime.now(timezone.utc).isoformat(),
        }
        await request.app.state.redis.publish(get_settings().access_events_channel, json.dumps(event))
    return response
