"""Service for creating and dispatching notifications."""
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.tenant import TenantConfig
from app.models.user import User

# Notification types that also trigger an email
_EMAIL_TYPES = {
    "ticket_created",
    "ticket_assigned",
    "status_changed",
    "comment_added",
    "sla_warning",
    "sla_breached",
    "ticket_resolved",
    "ticket_mentioned",
}


class NotificationService:
    """Create in-app notifications, publish to Redis pub/sub, and enqueue emails."""

    @staticmethod
    async def create_and_send(
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        notification_type: str,
        title: str,
        db: AsyncSession,
        *,
        ticket_id: uuid.UUID | None = None,
        body: str | None = None,
    ) -> Notification:
        """Persist a notification, publish to Redis, and optionally enqueue email.

        Args:
            user_id: Recipient user UUID.
            tenant_id: Owning tenant.
            notification_type: One of the defined type constants.
            title: Short notification title.
            db: Active async session.
            ticket_id: Related ticket UUID (optional).
            body: Longer description (optional).

        Returns:
            The persisted Notification ORM instance.
        """
        # Check business hours to decide whether to send email now or schedule it
        scheduled_for: datetime | None = None
        if notification_type in _EMAIL_TYPES:
            cfg_result = await db.execute(
                select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
            )
            config = cfg_result.scalar_one_or_none()
            if config is not None:
                from app.utils.business_hours import is_within_business_hours, next_business_start
                now = datetime.now(timezone.utc)
                if not is_within_business_hours(
                    now,
                    config.timezone,
                    config.working_days,
                    config.working_hours_start,
                    config.working_hours_end,
                ):
                    scheduled_for = next_business_start(
                        now,
                        config.timezone,
                        config.working_days,
                        config.working_hours_start,
                        config.working_hours_end,
                    )

        notification = Notification(
            user_id=user_id,
            tenant_id=tenant_id,
            type=notification_type,
            title=title,
            body=body,
            ticket_id=ticket_id,
            is_read=False,
            scheduled_for=scheduled_for,
            email_sent_at=None,
        )
        db.add(notification)
        await db.flush()

        # Publish to Redis pub/sub so connected WebSocket clients receive it instantly
        await NotificationService._publish_to_redis(notification)

        # Enqueue email if this notification type warrants one
        if notification_type in _EMAIL_TYPES:
            if scheduled_for is not None:
                # Outside business hours — email will be sent by the scheduled task
                pass
            else:
                user_result = await db.execute(
                    select(User.email).where(User.id == user_id)
                )
                user_email: str | None = user_result.scalar_one_or_none()
                if user_email:
                    notification.email_sent_at = datetime.now(timezone.utc)
                    NotificationService._enqueue_email(
                        to=user_email,
                        subject=title,
                        template=notification_type,
                        context={
                            "title": title,
                            "body": body,
                            "ticket_id": str(ticket_id) if ticket_id else None,
                            "type": notification_type,
                        },
                    )

        return notification

    @staticmethod
    async def _publish_to_redis(notification: Notification) -> None:
        """Publish a notification payload to Redis pub/sub channel."""
        try:
            import redis.asyncio as aioredis

            from app.config import settings

            payload = json.dumps(
                {
                    "id": str(notification.id),
                    "type": notification.type,
                    "title": notification.title,
                    "body": notification.body,
                    "ticket_id": str(notification.ticket_id) if notification.ticket_id else None,
                    "is_read": False,
                    "created_at": notification.created_at.isoformat()
                    if notification.created_at
                    else None,
                }
            )
            client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            try:
                await client.publish(f"notifications:{notification.user_id}", payload)
            finally:
                await client.aclose()
        except Exception:
            # Redis publish failure must not break the main request
            pass

    @staticmethod
    def _enqueue_email(to: str, subject: str, template: str, context: dict) -> None:
        """Enqueue an email task via Celery (best-effort)."""
        try:
            from app.tasks.email_tasks import send_notification_email

            send_notification_email.delay(
                to=to,
                subject=subject,
                template=template,
                context=context,
            )
        except Exception:
            pass
