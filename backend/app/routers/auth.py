import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from jose import JWTError
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser
from app.models.tenant import Tenant, TenantConfig
from app.models.user import User
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.config import settings

try:
    import redis as redis_lib
    redis_client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None

router = APIRouter()

REFRESH_TOKEN_COOKIE = "refresh_token"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    tenant_id: uuid.UUID
    avatar_url: str | None

    class Config:
        from_attributes = True


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )


def _store_refresh_token(user_id: uuid.UUID, jti: str) -> None:
    if redis_client:
        key = f"refresh:{user_id}:{jti}"
        redis_client.setex(key, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, "1")


def _revoke_refresh_token(user_id: uuid.UUID, jti: str) -> None:
    if redis_client:
        redis_client.delete(f"refresh:{user_id}:{jti}")


def _is_refresh_token_valid(user_id: uuid.UUID, jti: str) -> bool:
    if redis_client:
        return redis_client.exists(f"refresh:{user_id}:{jti}") == 1
    return True


@router.post("/login", response_model=TokenResponse)
async def login(
    login_request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email + password."""
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.slug == login_request.tenant_slug).where(Tenant.is_active.is_(True))
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    user_result = await db.execute(
        select(User)
        .where(User.tenant_id == tenant.id)
        .where(User.email == login_request.email.lower())
        .where(User.deleted_at.is_(None))
    )
    user = user_result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(login_request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    if user.is_archived:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account has been archived")

    await db.execute(
        update(User).where(User.id == user.id).values(last_login_at=datetime.now(timezone.utc))
    )
    await db.commit()

    access_token = create_access_token(user.id, tenant.id, user.role)
    refresh_token, jti = create_refresh_token(user.id, tenant.id)
    _store_refresh_token(user.id, jti)
    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Issue a new access token using the refresh token cookie."""
    token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise JWTError("Not a refresh token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = uuid.UUID(payload["sub"])
    tenant_id = uuid.UUID(payload["tenant_id"])
    jti = payload["jti"]

    if not _is_refresh_token_valid(user_id, jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    user_result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .where(User.tenant_id == tenant_id)
        .where(User.is_active.is_(True))
        .where(User.is_archived.is_(False))
        .where(User.deleted_at.is_(None))
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    _revoke_refresh_token(user_id, jti)
    new_access = create_access_token(user.id, tenant_id, user.role)
    new_refresh, new_jti = create_refresh_token(user.id, tenant_id)
    _store_refresh_token(user.id, new_jti)
    _set_refresh_cookie(response, new_refresh)

    return TokenResponse(access_token=new_access)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
) -> dict:
    """Revoke the refresh token and clear the cookie."""
    token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if token:
        try:
            payload = decode_token(token)
            user_id = uuid.UUID(payload["sub"])
            jti = payload["jti"]
            _revoke_refresh_token(user_id, jti)
        except Exception:
            pass

    response.delete_cookie(key=REFRESH_TOKEN_COOKIE, path="/api/v1/auth")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser) -> User:
    """Return the authenticated user's profile."""
    return current_user


@router.get("/login/azure")
async def azure_login() -> dict:
    """Return the Azure AD authorization URL."""
    if not settings.AZURE_CLIENT_ID or not settings.AZURE_TENANT_ID:
        raise HTTPException(status_code=400, detail="Azure AD not configured")

    import msal
    msal_app = msal.ConfidentialClientApplication(
        settings.AZURE_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}",
        client_credential=settings.AZURE_CLIENT_SECRET,
    )
    auth_url = msal_app.get_authorization_request_url(
        scopes=["User.Read"],
        redirect_uri=f"{settings.API_BASE_URL}/api/v1/auth/callback/azure",
    )
    return {"auth_url": auth_url}


@router.get("/callback/azure")
async def azure_callback(
    code: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Handle Azure AD OAuth2 callback."""
    if not settings.AZURE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Azure AD not configured")

    import msal
    msal_app = msal.ConfidentialClientApplication(
        settings.AZURE_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}",
        client_credential=settings.AZURE_CLIENT_SECRET,
    )
    result = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=["User.Read"],
        redirect_uri=f"{settings.API_BASE_URL}/api/v1/auth/callback/azure",
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result.get("error_description", "Azure auth failed"))

    claims = result.get("id_token_claims", {})
    azure_oid = claims.get("oid")
    email = claims.get("preferred_username", "").lower()
    full_name = claims.get("name", email)

    if not azure_oid or not email:
        raise HTTPException(status_code=400, detail="Could not extract user info from Azure token")

    config_result = await db.execute(
        select(TenantConfig).where(TenantConfig.azure_tenant_id == settings.AZURE_TENANT_ID)
    )
    tenant_config = config_result.scalar_one_or_none()
    if not tenant_config:
        raise HTTPException(status_code=404, detail="Tenant not configured for Azure AD")

    user_result = await db.execute(
        select(User)
        .where(User.tenant_id == tenant_config.tenant_id)
        .where(User.azure_oid == azure_oid)
        .where(User.deleted_at.is_(None))
    )
    user = user_result.scalar_one_or_none()

    if not user:
        user = User(
            tenant_id=tenant_config.tenant_id,
            email=email,
            full_name=full_name,
            azure_oid=azure_oid,
            role="requester",
        )
        db.add(user)
        await db.flush()

    if not user.is_active or user.is_archived:
        raise HTTPException(status_code=403, detail="Account is not active")

    await db.execute(
        update(User).where(User.id == user.id).values(last_login_at=datetime.now(timezone.utc))
    )
    await db.commit()

    access_token = create_access_token(user.id, tenant_config.tenant_id, user.role)
    refresh_token_str, jti = create_refresh_token(user.id, tenant_config.tenant_id)
    _store_refresh_token(user.id, jti)
    _set_refresh_cookie(response, refresh_token_str)

    # If a frontend URL is configured, redirect back to the frontend with the token
    if settings.FRONTEND_URL:
        redirect_url = f"{settings.FRONTEND_URL}/auth/azure-callback?token={access_token}"
        return RedirectResponse(url=redirect_url, status_code=302)

    return TokenResponse(access_token=access_token)
