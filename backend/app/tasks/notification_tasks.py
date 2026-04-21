"""Celery task for dispatching scheduled (off-hours) notification emails."""
import asyncio
import logging
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _send_scheduled_notifications_async() -> int:
    """Find notifications scheduled for delivery and send their emails.

    Returns:
        Number of emails dispatched.
    """
    from sqlalchemy import select, and_

    from app.database import async_session_factory
    import app.models  # noqa: F401 – registers all mappers before any query
    from app.models.notification import Notification
    from app.models.user import User

    now = datetime.now(timezone.utc)
    count = 0

    async with async_session_factory() as db:
        result = await db.execute(
            select(Notification)
            .where(
                and_(
                    Notification.scheduled_for.is_not(None),
                    Notification.scheduled_for <= now,
                    Notification.email_sent_at.is_(None),
                )
            )
        )
        notifications = result.scalars().all()

        for notif in notifications:
            try:
                user_result = await db.execute(
                    select(User.email).where(User.id == notif.user_id)
                )
                user_email: str | None = user_result.scalar_one_or_none()
                if user_email:
                    from app.tasks.email_tasks import send_notification_email
                    send_notification_email.delay(
                        to=user_email,
                        subject=notif.title,
                        template=notif.type,
                        context={
                            "title": notif.title,
                            "body": notif.body,
                            "ticket_id": str(notif.ticket_id) if notif.ticket_id else None,
                            "type": notif.type,
                        },
                        notification_id=str(notif.id),
                    )
                    notif.email_sent_at = now
                    count += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to send scheduled notification %s: %s", notif.id, exc)

        try:
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            logger.error("Failed to commit email_sent_at updates: %s", exc)
            return 0

    logger.info("Scheduled notifications: %d email(s) dispatched", count)
    return count


@celery_app.task(
    name="app.tasks.notification_tasks.send_scheduled_notifications",
    bind=True,
    max_retries=3,
)
def send_scheduled_notifications(self) -> dict:
    """Celery task: send emails for notifications created outside business hours.

    Scheduled every 5 minutes via Celery Beat.
    """
    try:
        count = _run_async(_send_scheduled_notifications_async())
        return {"status": "ok", "emails_sent": count}
    except Exception as exc:  # noqa: BLE001
        logger.exception("send_scheduled_notifications failed: %s", exc)
        raise self.retry(exc=exc, countdown=60) from exc
