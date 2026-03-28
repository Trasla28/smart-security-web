"""Celery tasks for SLA monitoring – breach detection and warning notifications."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in an event loop (e.g., during tests); create a new loop
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _check_sla_warnings_async() -> int:
    """Find tickets approaching SLA breach and enqueue warning notifications.

    Returns:
        Number of tickets processed.
    """
    from sqlalchemy import select, and_
    from app.database import async_session_factory
    from app.models.ticket import Ticket

    now = datetime.now(timezone.utc)
    warning_window_end = now + timedelta(hours=2)

    async with async_session_factory() as db:
        result = await db.execute(
            select(Ticket).where(
                and_(
                    Ticket.sla_due_at > now,
                    Ticket.sla_due_at <= warning_window_end,
                    Ticket.sla_breached.is_(False),
                    Ticket.deleted_at.is_(None),
                    Ticket.status.not_in(["resolved", "closed"]),
                )
            )
        )
        tickets = list(result.scalars().all())

        count = 0
        for ticket in tickets:
            try:
                # Enqueue a warning notification (email/in-app)
                # Import email_tasks here to avoid circular imports
                from app.tasks.email_tasks import send_sla_warning_email  # type: ignore[import]

                send_sla_warning_email.delay(
                    str(ticket.id),
                    str(ticket.tenant_id),
                    ticket.ticket_number,
                    ticket.sla_due_at.isoformat() if ticket.sla_due_at else None,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to enqueue SLA warning for ticket %s: %s",
                    ticket.ticket_number,
                    exc,
                )
            count += 1

        logger.info("SLA warning check complete – %d ticket(s) approaching breach", count)
        return count


async def _check_sla_breaches_async() -> int:
    """Mark overdue tickets as SLA-breached and enqueue critical notifications.

    Returns:
        Number of tickets marked as breached.
    """
    from sqlalchemy import select, and_
    from app.database import async_session_factory
    from app.models.ticket import Ticket

    now = datetime.now(timezone.utc)

    async with async_session_factory() as db:
        result = await db.execute(
            select(Ticket).where(
                and_(
                    Ticket.sla_due_at < now,
                    Ticket.sla_breached.is_(False),
                    Ticket.deleted_at.is_(None),
                    Ticket.status.not_in(["resolved", "closed"]),
                )
            )
        )
        tickets = list(result.scalars().all())

        count = 0
        for ticket in tickets:
            try:
                ticket.sla_breached = True
                await db.flush()

                # Enqueue critical notification
                from app.tasks.email_tasks import send_sla_breach_email  # type: ignore[import]

                send_sla_breach_email.delay(
                    str(ticket.id),
                    str(ticket.tenant_id),
                    ticket.ticket_number,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to process SLA breach for ticket %s: %s",
                    ticket.ticket_number,
                    exc,
                )
            count += 1

        try:
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            logger.error("Failed to commit SLA breach updates: %s", exc)
            return 0

        logger.info("SLA breach check complete – %d ticket(s) marked as breached", count)
        return count


@celery_app.task(name="app.tasks.sla_tasks.check_sla_warnings", bind=True, max_retries=3)
def check_sla_warnings(self) -> dict:
    """Celery task: find tickets within 2 hours of SLA breach and send warnings.

    Scheduled every 30 minutes via Celery Beat.
    """
    try:
        count = _run_async(_check_sla_warnings_async())
        return {"status": "ok", "warnings_sent": count}
    except Exception as exc:  # noqa: BLE001
        logger.exception("check_sla_warnings failed: %s", exc)
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(name="app.tasks.sla_tasks.check_sla_breaches", bind=True, max_retries=3)
def check_sla_breaches(self) -> dict:
    """Celery task: mark overdue tickets as SLA-breached and send critical alerts.

    Scheduled every 15 minutes via Celery Beat.
    """
    try:
        count = _run_async(_check_sla_breaches_async())
        return {"status": "ok", "breaches_processed": count}
    except Exception as exc:  # noqa: BLE001
        logger.exception("check_sla_breaches failed: %s", exc)
        raise self.retry(exc=exc, countdown=60) from exc
