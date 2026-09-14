import logging
import re
import time
from uuid import uuid4

from fastapi import Request, Response
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import RequestResponseEndpoint

from tshortner.core.logging import request_id_var

logger = logging.getLogger("tshortner.request")
_SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")


async def log_requests(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Gives each request an ID that every log line written while handling it carries, and logs one line per request."""
    incoming = request.headers.get("x-request-id", "")
    request_id = incoming if _SAFE_REQUEST_ID.fullmatch(incoming) else uuid4().hex
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request failed", extra=_summary(request, 500, started))
        response = PlainTextResponse("Internal Server Error", status_code=500)
    else:
        level = logging.WARNING if response.status_code >= 500 else logging.INFO
        logger.log(level, "request handled", extra=_summary(request, response.status_code, started))
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-ID"] = request_id
    return response


def _summary(request: Request, status: int, started: float) -> dict[str, object]:
    return {
        "method": request.method,
        "path": request.url.path,
        "status": status,
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        "client_ip": request.client.host if request.client else None,
    }
