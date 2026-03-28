"""Celery task for creating tickets from active recurring templates."""
import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _process_recurring_tickets_async() -> int:
    """Find due recurring templates and create a ticket for each.

    Returns:
        Number of tickets created successfully.
    """
    from sqlalchemy import and_, select

    from app.database import async_session_factory
    from app.models.area import Area
    from app.models.recurring import RecurringTemplate
    from app.models.tenant import TenantConfig
    from app.services.recurring_service import calculate_next_run

    now = datetime.now(timezone.utc)
    count = 0

    async with async_session_factory() as db:
        result = await db.execute(
            select(RecurringTemplate).where(
                and_(
                    RecurringTemplate.is_active.is_(True),
                    RecurringTemplate.next_run_at <= now,
                )
            )
        )
        templates = list(result.scalars().all())

        for template in templates:
            try:
                # Get tenant config for timezone and working days
                cfg_result = await db.execute(
                    select(TenantConfig).where(TenantConfig.tenant_id == template.tenant_id)
                )
                config = cfg_result.scalar_one_or_none()
                tz_str = config.timezone if config else "America/Bogota"
                working_days: list[int] = list(config.working_days) if config else [1, 2, 3, 4, 5]

                # Build ticket directly to avoid circular service imports
                from app.models.ticket import Ticket, TicketHistory
                from app.models.sla import SLA
                from app.utils.business_hours import calculate_due_date

                # Generate sequential ticket number
                from sqlalchemy import func, text

                await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:tid))"), {"tid": str(template.tenant_id)})
                max_result = await db.execute(
                    select(func.max(Ticket.ticket_number)).where(Ticket.tenant_id == template.tenant_id)
                )
                current_max: str | None = max_result.scalar_one_or_none()
                if current_max:
                    seq = int(current_max.replace("#TK-", "")) + 1
                else:
                    seq = 1
                ticket_number = f"#TK-{seq:04d}"

                # Find applicable SLA
                sla_result = await db.execute(
                    select(SLA)
                    .where(SLA.tenant_id == template.tenant_id)
                    .where(SLA.is_active.is_(True))
                    .where(
                        (SLA.category_id == template.category_id) | (SLA.category_id.is_(None))
                    )
                    .where(
                        (SLA.priority == template.priority) | (SLA.priority.is_(None))
                    )
                    .order_by(
                        SLA.category_id.is_(None),
                        SLA.priority.is_(None),
                    )
                )
                sla = sla_result.scalars().first()

                sla_due_at = None
                if sla and config:
                    sla_due_at = calculate_due_date(
                        start=now,
                        hours=sla.resolution_hours,
                        timezone_str=tz_str,
                        working_days=working_days,
                        working_hours_start=config.working_hours_start,
                        working_hours_end=config.working_hours_end,
                    )
                elif sla:
                    sla_due_at = calculate_due_date(start=now, hours=sla.resolution_hours)

                ticket = Ticket(
                    tenant_id=template.tenant_id,
                    ticket_number=ticket_number,
                    title=template.title,
                    description=template.description or f"Ticket recurrente: {template.title}",
                    status="open",
                    priority=template.priority,
                    category_id=template.category_id,
                    area_id=template.area_id,
                    requester_id=template.created_by,
                    assigned_to=template.assigned_to,
                    sla_id=sla.id if sla else None,
                    sla_due_at=sla_due_at,
                    sla_breached=False,
                    is_recurring_instance=True,
                    recurring_template_id=template.id,
                    reopen_count=0,
                )
                db.add(ticket)
                await db.flush()

                # Record history
                history = TicketHistory(
                    tenant_id=template.tenant_id,
                    ticket_id=ticket.id,
                    actor_id=None,  # System action
                    action="created",
                    new_value={"source": "recurring", "template_id": str(template.id)},
                )
                db.add(history)

                # Update template scheduling
                template.last_run_at = now
                template.next_run_at = calculate_next_run(
                    template,
                    after=now,
                    timezone_str=tz_str,
                    working_days=working_days,
                )

                count += 1
                logger.info(
                    "Created recurring ticket %s from template %s",
                    ticket_number,
                    template.id,
                )

            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to process recurring template %s: %s",
                    template.id,
                    exc,
                )

        try:
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to commit recurring ticket batch: %s", exc)
            await db.rollback()
            return 0

    logger.info("Recurring ticket processing complete – %d ticket(s) created", count)
    return count


@celery_app.task(
    name="app.tasks.recurring_tasks.process_recurring_tickets",
    bind=True,
    max_retries=3,
)
def process_recurring_tickets(self) -> dict:
    """Celery task: create tickets from active recurring templates that are due.

    Scheduled every hour via Celery Beat.
    """
    try:
        count = _run_async(_process_recurring_tickets_async())
        return {"status": "ok", "tickets_created": count}
    except Exception as exc:  # noqa: BLE001
        logger.exception("process_recurring_tickets failed: %s", exc)
        raise self.retry(exc=exc, countdown=60) from exc
