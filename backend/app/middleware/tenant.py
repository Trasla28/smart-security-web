import uuid

from fastapi import Request, Response
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.security import decode_token

EXEMPT_PATHS = {"/health", "/api/v1/auth/login", "/api/v1/auth/login/azure",
                "/api/v1/auth/callback/azure", "/api/v1/auth/refresh", "/docs",
                "/redoc", "/openapi.json"}


class TenantMiddleware(BaseHTTPMiddleware):
    """Extract tenant_id and user info from JWT and inject into request.state."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in EXEMPT_PATHS or request.url.path.startswith("/docs"):
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            request.state.tenant_id = None
            request.state.user_id = None
            request.state.user_role = None
            return await call_next(request)

        token = authorization.removeprefix("Bearer ").strip()
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                raise JWTError("Not an access token")
            request.state.tenant_id = uuid.UUID(payload["tenant_id"])
            request.state.user_id = uuid.UUID(payload["sub"])
            request.state.user_role = payload["role"]
        except (JWTError, KeyError, ValueError):
            request.state.tenant_id = None
            request.state.user_id = None
            request.state.user_role = None

        return await call_next(request)
