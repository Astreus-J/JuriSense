"""Adaptadores de e-mail: console (dev) e SMTP (produção, via env)."""

import logging
import smtplib
from email.message import EmailMessage

import anyio

from app.core.config import get_settings

logger = logging.getLogger("jurisense.email")


class ConsoleEmailSender:
    """Escreve o e-mail no log — usado quando SMTP_HOST não está configurado."""

    async def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info("E-mail para %s | %s\n%s", to, subject, body)


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


class FakeOABValidator:
    """Stub de desenvolvimento: considera qualquer OAB registrada.

    A integração real com a API da OAB substitui esta classe sem tocar
    nos casos de uso (porta OABValidator).
    """

    async def is_registered(self, oab: str, uf: str) -> bool:
        return True
