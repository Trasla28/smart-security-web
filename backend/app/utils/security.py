import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: uuid.UUID, tenant_id: uuid.UUID, role: str) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> tuple[str, str]:
    """Create a long-lived JWT refresh token. Returns (token, jti)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "type": "refresh",
        "iat": now,
        "exp": expire,
        "jti": jti,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Raises JWTError if invalid."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def generate_signed_url_token(file_path: str, expires_in: int = 3600) -> str:
    """Generate an HMAC-signed token for secure file download URLs."""
    expiry = int((datetime.now(timezone.utc) + timedelta(seconds=expires_in)).timestamp())
    message = f"{file_path}:{expiry}"
    signature = hmac.new(settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{signature}:{expiry}"


def verify_signed_url_token(file_path: str, token: str) -> bool:
    """Verify an HMAC-signed URL token."""
    try:
        signature, expiry_str = token.rsplit(":", 1)
        expiry = int(expiry_str)
        if datetime.now(timezone.utc).timestamp() > expiry:
            return False
        message = f"{file_path}:{expiry}"
        expected = hmac.new(settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    except (ValueError, AttributeError):
        return False
