"""Email adapters: console (dev) and SMTP (production, via env)."""

import logging
import smtplib
from email.message import EmailMessage

import anyio

from app.core.config import get_settings

logger = logging.getLogger("jurisense.email")


class ConsoleEmailSender:
    """Writes the email to the log — used when SMTP_HOST is not configured."""

    async def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info("Email to %s | %s\n%s", to, subject, body)


class SMTPEmailSender:
    async def send(self, *, to: str, subject: str, body: str) -> None:
        settings = get_settings()
        message = EmailMessage()
        message["From"] = settings.email_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        def _send_sync() -> None:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                smtp.starttls()
                if settings.smtp_user and settings.smtp_password:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(message)

        await anyio.to_thread.run_sync(_send_sync)
