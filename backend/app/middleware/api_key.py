from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_PUBLIC_PATHS = frozenset({"/health", "/docs", "/openapi.json", "/redoc"})


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Require X-API-Key when FINSIGHT_API_KEY is configured."""

    def __init__(self, app: object, api_key: str) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.api_key = api_key

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if not self.api_key or request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "")
        if provided != self.api_key:
            return JSONResponse(
                {"detail": "Invalid or missing API key"},
                status_code=401,
            )
        return await call_next(request)
