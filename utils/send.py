"""Shared email-sending utilities used by both mailer and preset_mailer."""
from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import smtp_settings


def send_email_sync(
    sender_name: str,
    recipient: str,
    subject: str,
    html_body: str,
) -> None:
    """Blocking SMTP call — runs inside a thread-pool executor."""
    cfg = smtp_settings.current  # always read the live singleton

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{sender_name} <{cfg.user}>"
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    ctx = ssl.create_default_context()
    if cfg.use_ssl:
        # Implicit SSL/TLS (e.g. port 465)
        with smtplib.SMTP_SSL(cfg.host, cfg.port, context=ctx, timeout=30) as smtp:
            smtp.login(cfg.user, cfg.password)
            smtp.sendmail(cfg.user, recipient, msg.as_string())
    else:
        # Opportunistic STARTTLS (e.g. port 587)
        with smtplib.SMTP(cfg.host, cfg.port, timeout=30) as smtp:
            smtp.ehlo()
            if smtp.has_extn("STARTTLS"):
                smtp.starttls(context=ctx)
                smtp.ehlo()
            smtp.login(cfg.user, cfg.password)
            smtp.sendmail(cfg.user, recipient, msg.as_string())


async def send_email(
    sender_name: str,
    recipient: str,
    subject: str,
    html_body: str,
) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, send_email_sync, sender_name, recipient, subject, html_body
    )
