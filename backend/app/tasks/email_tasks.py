import asyncio

from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.email_tasks.send_notification_email", bind=True, max_retries=3)
def send_notification_email(self, to: str, subject: str, template: str, context: dict) -> None:
    """Send a notification email by rendering a Jinja2 template.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        template: Template name (without .html extension).
        context: Variables passed to the template renderer.
    """
    from app.utils.email import send_email

    try:
        asyncio.run(send_email(to=to, subject=subject, template_name=template, context=context))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
