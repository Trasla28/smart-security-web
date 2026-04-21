import asyncio
import logging
import uuid

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _mark_email_sent(notification_id: str) -> None:
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.database import async_session_factory
    from app.models.notification import Notification

    async with async_session_factory() as db:
        result = await db.execute(
            select(Notification).where(Notification.id == uuid.UUID(notification_id))
        )
        notif = result.scalar_one_or_none()
        if notif and notif.email_sent_at is None:
            notif.email_sent_at = datetime.now(timezone.utc)
            await db.commit()


@celery_app.task(name="app.tasks.email_tasks.send_notification_email", bind=True, max_retries=3)
def send_notification_email(
    self,
    to: str,
    subject: str,
    template: str,
    context: dict,
    notification_id: str | None = None,
) -> None:
    from app.utils.email import send_email

    try:
        asyncio.run(send_email(to=to, subject=subject, template_name=template, context=context))
    except Exception as exc:
        logger.warning(
            "Email send failed (attempt %d/3) to=%s template=%s: %s",
            self.request.retries + 1,
            to,
            template,
            exc,
        )
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

    if notification_id:
        try:
            asyncio.run(_mark_email_sent(notification_id))
        except Exception as exc:
            logger.warning("Could not mark notification %s as email_sent_at: %s", notification_id, exc)
