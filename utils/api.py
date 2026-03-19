"""
API clients for SMSSEND and MAILBUY services.
"""
import json
import logging
import aiohttp

logger = logging.getLogger(__name__)

from config import (
    SMSSEND_ACCOUNT, SMSSEND_PASSWORD, SMSSEND_API_URL,
    MAILBUY_API_URL, MAILBUY_TOKEN,
    CRYPTOBOT_TOKEN, XROCKET_API_KEY,
)


# ─────────────────────── SMSSEND ───────────────────────

async def smssend_send_sms(phone: str, sender: str, message: str) -> dict:
    """
    Send SMS via SMSSEND API.

    Endpoint: POST /api/send
    Request params:
        account  – SMSSEND account
        password – SMSSEND password
        to       – recipient phone (international format, e.g. +41791234567)
        from     – sender name (max 12 chars alphanumeric)
        text     – message body (max 160 chars)
    Response (JSON):
        { "status": "ok"|"error", "id": "<msg_id>", "message": "<description>" }
    """
    url = f"{SMSSEND_API_URL}/api/send"
    payload = {
        "account": SMSSEND_ACCOUNT,
        "password": SMSSEND_PASSWORD,
        "to": phone,
        "from": sender,
        "text": message,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                data = await resp.json(content_type=None)
                return data
    except aiohttp.ClientError as exc:
        return {"status": "error", "message": str(exc)}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


async def smssend_get_balance() -> dict:
    """
    Get SMSSEND account balance.

    Endpoint: GET /api/balance
    Request params: account, password
    Response: { "status": "ok", "balance": <float> }
    """
    url = f"{SMSSEND_API_URL}/api/balance"
    params = {"account": SMSSEND_ACCOUNT, "password": SMSSEND_PASSWORD}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json(content_type=None)
                return data
    except aiohttp.ClientError as exc:
        return {"status": "error", "message": str(exc)}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


# ─────────────────────── MAILBUY ───────────────────────

def _mailbuy_headers() -> dict:
    return {
        "Authorization": f"Bearer {MAILBUY_TOKEN}",
        "Content-Type": "application/json",
    }


async def mailbuy_get_domains() -> list[dict]:
    """
    Get available mail domains with prices.

    Endpoint: GET /v1/domains
    Response: { "domains": [ { "name": "...", "price": <float> }, ... ] }
    """
    url = f"{MAILBUY_API_URL}/v1/domains"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=_mailbuy_headers(), timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                data = await resp.json(content_type=None)
                return data.get("domains", [])
    except aiohttp.ClientError as exc:
        logger.error("MAILBUY get_domains ClientError: %s", exc)
        return []
    except Exception as exc:
        logger.error("MAILBUY get_domains error: %s", exc)
        return []


async def mailbuy_buy_account(domain: str) -> dict:
    """
    Purchase a mail account for a given domain.

    Endpoint: POST /v1/accounts
    Request body: { "domain": "<domain>" }
    Response:
        {
          "id": "<account_id>",
          "email": "<email@domain>",
          "domain": "<domain>",
          "price": <float>,
          "status": "active"|"pending",
          "code": "<activation_code>",
          "link": "<activation_link>"
        }
    """
    url = f"{MAILBUY_API_URL}/v1/accounts"
    payload = {"domain": domain}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=_mailbuy_headers(), json=payload,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                data = await resp.json(content_type=None)
                return data
    except aiohttp.ClientError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        return {"error": str(exc)}


async def mailbuy_check_messages(account_id: str) -> dict:
    """
    Check messages for a purchased mail account.

    Endpoint: GET /v1/accounts/{account_id}/messages
    Response:
        { "messages": [ { ... } ], "count": <int> }
    """
    url = f"{MAILBUY_API_URL}/v1/accounts/{account_id}/messages"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=_mailbuy_headers(), timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                data = await resp.json(content_type=None)
                return data
    except aiohttp.ClientError as exc:
        return {"messages": [], "count": 0, "error": str(exc)}
    except Exception as exc:
        return {"messages": [], "count": 0, "error": str(exc)}


# ─────────────────────── CRYPTOBOT ───────────────────────

async def cryptobot_create_invoice(amount: float, currency: str = "USDT") -> dict:
    """
    Create a CryptoBot invoice.

    Endpoint: POST https://pay.crypt.bot/api/createInvoice
    Headers: Crypto-Pay-API-Token: <token>
    Body: { "asset": <currency>, "amount": <amount> }
    Response: { "ok": true, "result": { "invoice_id": ..., "pay_url": ... } }
    """
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    payload = {"asset": currency, "amount": str(amount)}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                return await resp.json(content_type=None)
    except aiohttp.ClientError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def cryptobot_check_invoice(invoice_id: str) -> dict:
    """
    Check CryptoBot invoice status.

    Endpoint: GET https://pay.crypt.bot/api/getInvoices
    Params: invoice_ids=<id>
    Response: { "ok": true, "result": { "items": [ { "status": "paid"|"active", ... } ] } }
    """
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    params = {"invoice_ids": invoice_id}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                return await resp.json(content_type=None)
    except aiohttp.ClientError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ─────────────────────── XROCKET ───────────────────────

async def xrocket_create_invoice(amount: float, currency: str = "USDT") -> dict:
    """
    Create an xRocket invoice.

    Endpoint: POST https://pay.xrocket.tg/tg-invoices
    Headers: Rocket-Pay-Key: <key>
    Body: { "currency": <currency>, "amount": <amount>, "description": "Balance top-up" }
    Response: { "success": true, "data": { "id": ..., "link": ... } }
    """
    url = "https://pay.xrocket.tg/tg-invoices"
    headers = {
        "Rocket-Pay-Key": XROCKET_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "currency": currency,
        "amount": amount,
        "description": "Balance top-up",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                return await resp.json(content_type=None)
    except aiohttp.ClientError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def xrocket_check_invoice(invoice_id: str) -> dict:
    """
    Check xRocket invoice status.

    Endpoint: GET https://pay.xrocket.tg/tg-invoices/{invoice_id}
    Headers: Rocket-Pay-Key: <key>
    Response: { "success": true, "data": { "status": "paid"|"active", ... } }
    """
    url = f"https://pay.xrocket.tg/tg-invoices/{invoice_id}"
    headers = {"Rocket-Pay-Key": XROCKET_API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                return await resp.json(content_type=None)
    except aiohttp.ClientError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
