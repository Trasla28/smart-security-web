from celery import Celery

from app.config import settings

celery_app = Celery(
    "tickets",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.recurring_tasks",
        "app.tasks.report_tasks",
        "app.tasks.sla_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-sla-warnings": {
            "task": "app.tasks.sla_tasks.check_sla_warnings",
            "schedule": 1800.0,  # every 30 min
        },
        "check-sla-breaches": {
            "task": "app.tasks.sla_tasks.check_sla_breaches",
            "schedule": 900.0,  # every 15 min
        },
        "process-recurring-tickets": {
            "task": "app.tasks.recurring_tasks.process_recurring_tickets",
            "schedule": 3600.0,  # every hour
        },
    },
)
