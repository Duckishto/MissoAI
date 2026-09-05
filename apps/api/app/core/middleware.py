import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

log = get_logger("http")

REQUEST_ID_HEADER = "x-request-id"
CF_RAY_HEADER = "cf-ray"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Bind one id to every log line and every AI call in a request.

    The Worker forwards CF-Ray, so a browser network entry, a Worker log,
    a container log and an ai_runs row can all be joined on the same id.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = (
            request.headers.get(REQUEST_ID_HEADER)
            or request.headers.get(CF_RAY_HEADER)
            or uuid.uuid4().hex
        )
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id

        started = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            log.exception(
                "request_failed", method=request.method, path=request.url.path
            )
            raise
        duration_ms = round((time.perf_counter() - started) * 1000, 2)

        response.headers[REQUEST_ID_HEADER] = request_id
        log.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response
