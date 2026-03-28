"""Email sending utility using aiosmtplib and Jinja2 templates."""
import pathlib

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings

_TEMPLATES_DIR = pathlib.Path(__file__).parent.parent / "templates" / "emails"

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


async def send_email(
    to: str,
    subject: str,
    template_name: str,
    context: dict,
) -> None:
    """Render a Jinja2 HTML email template and send it via SMTP.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        template_name: Template filename (without .html extension).
        context: Variables passed to the template.
    """
    template = _jinja_env.get_template(f"{template_name}.html")
    html_body = template.render(**context)

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message.attach(MIMEText(html_body, "html", "utf-8"))

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER or None,
        password=settings.SMTP_PASSWORD or None,
        use_tls=False,
        start_tls=settings.SMTP_TLS,
    )
