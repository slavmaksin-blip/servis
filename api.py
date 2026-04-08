"""Async client for the Mensor Partner API."""

from __future__ import annotations

import os
import httpx

MENSOR_API_URL = os.getenv("MENSOR_API_URL", "http://localhost:8080")
MENSOR_API_KEY = os.getenv("MENSOR_API_KEY", "")

_HEADERS = {
    "X-API-Key": MENSOR_API_KEY,
    "Content-Type": "application/json",
}


async def ping() -> dict:
    """Health-check, no auth required."""
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{MENSOR_API_URL}/api/v1/ping", timeout=10)
        return r.json()


async def send_sms(phone: str, text: str, sender: str = "") -> dict:
    """Send an SMS via TraffikLink.

    Returns the API response dict, e.g. ``{"ok": True, "sms_id": "..."}``
    or ``{"ok": False, "error": "..."}``.
    """
    payload: dict = {"phone": phone, "text": text}
    if sender:
        payload["sender"] = sender
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{MENSOR_API_URL}/api/v1/sms/send",
            headers=_HEADERS,
            json=payload,
            timeout=15,
        )
    return r.json()


async def send_email(
    recipient: str,
    subject: str,
    sender_name: str,
    html_body: str,
) -> dict:
    """Send an HTML email via the configured SMTP pool.

    Returns ``{"ok": True}`` on success or ``{"ok": False, "error": "..."}``.
    """
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{MENSOR_API_URL}/api/v1/mail/send",
            headers=_HEADERS,
            json={
                "recipient": recipient,
                "subject": subject,
                "sender_name": sender_name,
                "html_body": html_body,
            },
            timeout=15,
        )
    return r.json()


async def generate_screen(
    country: str,
    platform: str,
    service_name: str,
    amount: float,
) -> tuple[bytes | None, str | None]:
    """Generate a fake bank-screenshot PNG.

    Returns ``(image_bytes, None)`` on success or ``(None, error_message)``.
    """
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{MENSOR_API_URL}/api/v1/screen/generate",
            headers=_HEADERS,
            json={
                "country": country,
                "platform": platform,
                "service_name": service_name,
                "amount": amount,
            },
            timeout=30,
        )
    if r.status_code == 200:
        return r.content, None
    error = r.json().get("error", f"HTTP {r.status_code}")
    return None, error


async def generate_pdf(
    template: str,
    lang: str,
    buyer_name: str,
    delivery: str,
    product_name: str,
    amount: str,
    link: str,
) -> tuple[bytes | None, str | None, str]:
    """Generate a Switzerland promo PDF (Ricardo or PostFinance/Post).

    Returns ``(pdf_bytes, None, filename)`` on success
    or ``(None, error_message, "")``.
    """
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{MENSOR_API_URL}/api/v1/pdf/generate",
            headers=_HEADERS,
            json={
                "template": template,
                "lang": lang,
                "buyer_name": buyer_name,
                "delivery": delivery,
                "product_name": product_name,
                "amount": amount,
                "link": link,
            },
            timeout=30,
        )
    if r.status_code == 200:
        filename = "document.pdf"
        cd = r.headers.get("Content-Disposition", "")
        if 'filename="' in cd:
            filename = cd.split('filename="')[1].rstrip('"')
        return r.content, None, filename
    error = r.json().get("error", f"HTTP {r.status_code}")
    return None, error, ""
