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


async def _send_sla_notifications_async(
    ticket_id: str,
    tenant_id: str,
    notification_type: str,
    title: str,
    body: str,
) -> None:
    """Find the assigned agent (and area admins as fallback) and send SLA notifications."""
    from sqlalchemy import select, and_
    from app.database import async_session_factory
    import app.models  # noqa: F401 – registers all mappers before any query
    from app.models.ticket import Ticket
    from app.models.user import User
    from app.models.area import UserArea
    from app.services.notification_service import NotificationService

    t_id = uuid.UUID(ticket_id)
    tn_id = uuid.UUID(tenant_id)

    async with async_session_factory() as db:
        result = await db.execute(
            select(Ticket).where(and_(Ticket.id == t_id, Ticket.tenant_id == tn_id))
        )
        ticket = result.scalar_one_or_none()
        if not ticket:
            return

        notify_ids: set[uuid.UUID] = set()

        if ticket.assigned_to:
            notify_ids.add(ticket.assigned_to)
        else:
            # No agent — notify area admins/supervisors
            if ticket.area_id:
                sup_result = await db.execute(
                    select(User.id)
                    .join(UserArea, UserArea.user_id == User.id)
                    .where(
                        and_(
                            UserArea.area_id == ticket.area_id,
                            User.tenant_id == tn_id,
                            User.role.in_(["admin", "supervisor"]),
                            User.deleted_at.is_(None),
                            User.is_active.is_(True),
                        )
                    )
                )
                for row in sup_result.scalars().all():
                    notify_ids.add(row)

        # Always notify tenant admins
        admin_result = await db.execute(
            select(User.id).where(
                and_(
                    User.tenant_id == tn_id,
                    User.role == "admin",
                    User.deleted_at.is_(None),
                    User.is_active.is_(True),
                )
            )
        )
        for row in admin_result.scalars().all():
            notify_ids.add(row)

        for uid in notify_ids:
            await NotificationService.create_and_send(
                user_id=uid,
                tenant_id=tn_id,
                notification_type=notification_type,
                title=title,
                db=db,
                ticket_id=ticket.id,
                body=body,
            )

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


@celery_app.task(name="app.tasks.email_tasks.send_sla_warning_email", bind=True, max_retries=3)
def send_sla_warning_email(
    self,
    ticket_id: str,
    tenant_id: str,
    ticket_number: str,
    sla_due_at: str | None,
) -> None:
    try:
        due_str = f" Vence: {sla_due_at[:16].replace('T', ' ')} UTC." if sla_due_at else ""
        asyncio.run(
            _send_sla_notifications_async(
                ticket_id=ticket_id,
                tenant_id=tenant_id,
                notification_type="sla_warning",
                title=f"⚠️ SLA por vencer: #{ticket_number}",
                body=f"El ticket #{ticket_number} está próximo a vencer su SLA.{due_str}",
            )
        )
    except Exception as exc:
        logger.warning("send_sla_warning_email failed for ticket %s: %s", ticket_number, exc)
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(name="app.tasks.email_tasks.send_sla_breach_email", bind=True, max_retries=3)
def send_sla_breach_email(
    self,
    ticket_id: str,
    tenant_id: str,
    ticket_number: str,
) -> None:
    try:
        asyncio.run(
            _send_sla_notifications_async(
                ticket_id=ticket_id,
                tenant_id=tenant_id,
                notification_type="sla_breached",
                title=f"🚨 SLA vencido: #{ticket_number}",
                body=f"El ticket #{ticket_number} ha superado su tiempo límite de SLA.",
            )
        )
    except Exception as exc:
        logger.warning("send_sla_breach_email failed for ticket %s: %s", ticket_number, exc)
        raise self.retry(exc=exc, countdown=60) from exc
