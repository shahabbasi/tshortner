import functools
import inspect
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from fastapi import Request, Response
from redis.asyncio import Redis

from tshortner.api.deps import RedisDep
from tshortner.core.config import get_settings

logger = logging.getLogger(__name__)

Endpoint = Callable[..., Awaitable[Response]]


def record_short_link_access(endpoint: Endpoint) -> Endpoint:
    """Publishes an access event each time the decorated endpoint redirects; AccessLogWorker persists them.

    The endpoint needs a `short_code` parameter. The request and Redis client are appended to its signature
    here, so FastAPI injects them without the endpoint having to declare them.
    """
    signature = inspect.signature(endpoint)

    @functools.wraps(endpoint)
    async def wrapper(*, _access_request: Request, _access_redis: Redis, **kwargs: object) -> Response:
        response = await endpoint(**kwargs)
        if response.status_code == 302:
            request = _access_request
            event = {
                "short_code": kwargs["short_code"],
                "ip_address": request.client.host if request.client else "unknown",
                "accessed_at": datetime.now(timezone.utc).isoformat(),
            }
            await _access_redis.publish(get_settings().access_events_channel, json.dumps(event))
            logger.debug("published access event", extra={"short_code": event["short_code"]})
        return response

    wrapper.__signature__ = signature.replace(
        parameters=[
            *signature.parameters.values(),
            inspect.Parameter("_access_request", inspect.Parameter.KEYWORD_ONLY, annotation=Request),
            inspect.Parameter("_access_redis", inspect.Parameter.KEYWORD_ONLY, annotation=RedisDep),
        ]
    )
    return wrapper
