"""Celery task for sending weekly summary reports."""
import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

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


async def _send_weekly_report_async(tenant_id_str: str) -> dict:
    """Build weekly report metrics and enqueue emails to configured recipients."""
    from sqlalchemy import select

    from app.database import async_session_factory
    from app.models.tenant import TenantConfig
    from app.repositories.dashboard_repository import DashboardRepository
    from app.tasks.email_tasks import send_notification_email

    tenant_id = uuid.UUID(tenant_id_str)
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=7)

    async with async_session_factory() as db:
        cfg_result = await db.execute(
            select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        )
        config = cfg_result.scalar_one_or_none()

        if not config or not config.weekly_report_enabled:
            return {"status": "skipped", "reason": "report disabled or no config"}

        recipients: list[str] = list(config.weekly_report_recipients or [])
        if not recipients:
            return {"status": "skipped", "reason": "no recipients configured"}

        summary = await DashboardRepository.get_summary(tenant_id, db, date_range_days=7)
        by_area = await DashboardRepository.get_tickets_by_area(tenant_id, db, date_range_days=7)
        by_status = await DashboardRepository.get_tickets_by_status(tenant_id, db)
        agents = await DashboardRepository.get_agent_performance(tenant_id, db, date_range_days=7)

    context = {
        "period_start": period_start.isoformat(),
        "period_end": now.isoformat(),
        "summary": summary,
        "tickets_by_area": by_area,
        "tickets_by_status": by_status,
        "top_agents": agents[:5],
    }

    sent = 0
    for email in recipients:
        try:
            send_notification_email.delay(
                to=email,
                subject=f"Reporte semanal de tickets – {now.strftime('%d/%m/%Y')}",
                template="weekly_report",
                context=context,
            )
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to enqueue weekly report email to %s: %s", email, exc)

    logger.info("Weekly report for tenant %s dispatched to %d recipient(s)", tenant_id_str, sent)
    return {"status": "ok", "recipients": sent}


@celery_app.task(
    name="app.tasks.report_tasks.send_weekly_report",
    bind=True,
    max_retries=3,
)
def send_weekly_report(self, tenant_id: str) -> dict:
    """Celery task: generate and email the weekly ticket summary report.

    Scheduled every Monday at 08:00 (tenant local time) via Celery Beat.
    """
    try:
        return _run_async(_send_weekly_report_async(tenant_id))
    except Exception as exc:  # noqa: BLE001
        logger.exception("send_weekly_report failed for tenant %s: %s", tenant_id, exc)
        raise self.retry(exc=exc, countdown=120) from exc
