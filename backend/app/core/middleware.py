"""Production Security & Correlation ID Middlewares for FastAPI."""

import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

HEADER_CORRELATION_ID = "X-Correlation-ID"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware that injects or propagates X-Correlation-ID across HTTP request lifecycles."""

    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get(HEADER_CORRELATION_ID) or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        response = await call_next(request)
        response.headers[HEADER_CORRELATION_ID] = correlation_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing standard HTTP production security headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
