"""
SMSSEND API client for smssend.su.

Endpoint: POST https://smssend.su/api/send
Auth: ``apikey`` query/form parameter.

Request fields
--------------
apikey  : str  – API key from account settings
phone   : str  – recipient phone in international format (e.g. 79991234567)
text    : str  – message text (up to 160 chars for single SMS)
sender  : str  – sender ID shown to recipient (max 11 alphanumeric chars)

Response JSON (success)
-----------------------
{"status": "ok", "id": "123456"}

Response JSON (error)
---------------------
{"status": "error", "message": "description"}
"""

import httpx
from typing import Optional

SMSSEND_BASE_URL = "https://smssend.su/api"


async def send_sms(
    api_key: str,
    phone: str,
    message: str,
    sender: str,
) -> dict:
    """
    Send an SMS via SMSSEND API.

    Returns a dict::

        {
            "success":    bool,
            "status":     str,   # "ok" | "error" | HTTP-error description
            "message_id": str | None,
            "raw":        dict,
        }
    """
    url = f"{SMSSEND_BASE_URL}/send"
    # Strip leading '+' so the phone contains digits only, as required by the API
    phone_digits = phone.lstrip("+").replace(" ", "").replace("-", "")
    payload = {
        "apikey": api_key,
        "phone": phone_digits,
        "text": message,
        "sender": sender,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, data=payload)
            response.raise_for_status()
            data = response.json()
            success = data.get("status") == "ok"
            return {
                "success": success,
                "status": data.get("status", "unknown"),
                "message_id": str(data["id"]) if data.get("id") is not None else None,
                "error": data.get("message") if not success else None,
                "raw": data,
            }
    except httpx.HTTPStatusError as exc:
        return {
            "success": False,
            "status": f"HTTP {exc.response.status_code}",
            "message_id": None,
            "error": str(exc),
            "raw": {},
        }
    except httpx.HTTPError as exc:
        return {
            "success": False,
            "status": "connection_error",
            "message_id": None,
            "error": str(exc),
            "raw": {},
        }
    except Exception as exc:
        return {
            "success": False,
            "status": "unexpected_error",
            "message_id": None,
            "error": str(exc),
            "raw": {},
        }


async def get_balance(api_key: str) -> Optional[float]:
    """Fetch SMSSEND account balance. Returns None on any error."""
    url = f"{SMSSEND_BASE_URL}/balance"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params={"apikey": api_key})
            response.raise_for_status()
            data = response.json()
            balance = data.get("balance")
            return float(balance) if balance is not None else None
    except Exception:
        return None


COUNTRIES = [
    {"name": "🇨🇭 Швейцария (+41)", "code": "41", "prefix": "+41"},
    {"name": "🇩🇪 Германия (+49)", "code": "49", "prefix": "+49"},
    {"name": "🇷🇺 Россия (+7)", "code": "7", "prefix": "+7"},
    {"name": "🇺🇸 США (+1)", "code": "1", "prefix": "+1"},
    {"name": "🇬🇧 Великобритания (+44)", "code": "44", "prefix": "+44"},
    {"name": "🇫🇷 Франция (+33)", "code": "33", "prefix": "+33"},
    {"name": "🇮🇹 Италия (+39)", "code": "39", "prefix": "+39"},
    {"name": "🇪🇸 Испания (+34)", "code": "34", "prefix": "+34"},
]


def get_country_prefix(code: str) -> Optional[str]:
    for c in COUNTRIES:
        if c["code"] == code:
            return c["prefix"]
    return None
