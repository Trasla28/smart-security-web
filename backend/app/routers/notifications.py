"""Notification endpoints — REST (list, mark-read) and WebSocket."""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser
from app.models.notification import Notification
from app.models.user import User
from app.schemas.common import PaginatedResponse

router = APIRouter()

# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: str | None
    ticket_id: uuid.UUID | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse)
async def list_notifications(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    unread_only: bool = False,
) -> dict:
    """Return paginated notifications for the authenticated user.

    Args:
        page: Page number (1-based).
        size: Items per page.
        unread_only: When true, only return unread notifications.
    """
    query = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .where(Notification.tenant_id == current_user.tenant_id)
        .order_by(Notification.created_at.desc())
    )

    if unread_only:
        query = query.where(Notification.is_read.is_(False))

    count_query = select(Notification.id).where(
        Notification.user_id == current_user.id,
        Notification.tenant_id == current_user.tenant_id,
    )
    if unread_only:
        count_query = count_query.where(Notification.is_read.is_(False))

    total_result = await db.execute(count_query)
    total = len(total_result.all())

    offset = (page - 1) * size
    result = await db.execute(query.offset(offset).limit(size))
    items = result.scalars().all()

    pages = max(1, -(-total // size)) if total > 0 else 1
    return {
        "items": [NotificationResponse.model_validate(n) for n in items],
        "total": total,
        "page": page,
        "pages": pages,
        "size": size,
    }


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Mark all unread notifications for the current user as read."""
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id)
        .where(Notification.tenant_id == current_user.tenant_id)
        .where(Notification.is_read.is_(False))
        .values(is_read=True, read_at=now)
    )
    await db.commit()


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_one_read(
    notification_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """Mark a single notification as read.

    Args:
        notification_id: Target notification UUID.

    Raises:
        HTTPException 404: If the notification does not belong to the current user.
    """
    result = await db.execute(
        select(Notification)
        .where(Notification.id == notification_id)
        .where(Notification.user_id == current_user.id)
        .where(Notification.tenant_id == current_user.tenant_id)
    )
    notification: Notification | None = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(notification)

    return NotificationResponse.model_validate(notification)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/ws")
async def notifications_ws(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
) -> None:
    """WebSocket endpoint for real-time notifications.

    The client must pass the JWT access token as a query parameter:
    ``wss://host/api/v1/notifications/ws?token=<access_token>``

    Once connected, the server subscribes to the Redis pub/sub channel
    ``notifications:{user_id}`` and forwards every message to the client.
    """
    # Authenticate before accepting the connection
    user_id, tenant_id = _authenticate_ws_token(token)
    if user_id is None:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    try:
        import redis.asyncio as aioredis

        from app.config import settings

        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"notifications:{user_id}")

        try:
            while True:
                # Check for incoming Redis messages (non-blocking)
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=30.0,
                )
                if message and message.get("type") == "message":
                    await websocket.send_text(message["data"])

                # Send a heartbeat ping every 30 s to keep the connection alive
                await websocket.send_json({"type": "ping"})

        except asyncio.TimeoutError:
            pass
        finally:
            await pubsub.unsubscribe(f"notifications:{user_id}")
            await pubsub.aclose()
            await redis_client.aclose()

    except WebSocketDisconnect:
        pass


def _authenticate_ws_token(token: str) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """Decode a JWT access token for WebSocket authentication.

    Returns:
        ``(user_id, tenant_id)`` on success, ``(None, None)`` on failure.
    """
    try:
        from jose import JWTError

        from app.utils.security import decode_token

        payload = decode_token(token)
        if payload.get("type") == "refresh":
            return None, None
        return uuid.UUID(payload["sub"]), uuid.UUID(payload["tenant_id"])
    except Exception:
        return None, None
