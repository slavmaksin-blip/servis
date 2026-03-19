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
    Returns a dict with keys: success (bool), status (str), message_id (str|None).
    """
    url = f"{SMSSEND_BASE_URL}/send"
    params = {
        "token": api_key,
        "to": phone,
        "txt": message,
        "from": sender,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, data=params)
            response.raise_for_status()
            data = response.json()
            success = data.get("status") == "ok" or data.get("error") is None
            return {
                "success": success,
                "status": data.get("status", "unknown"),
                "message_id": data.get("id"),
                "raw": data,
            }
    except httpx.HTTPError as exc:
        return {
            "success": False,
            "status": f"HTTP error: {exc}",
            "message_id": None,
            "raw": {},
        }


async def get_balance(api_key: str) -> Optional[float]:
    """Fetch SMSSEND account balance."""
    url = f"{SMSSEND_BASE_URL}/balance"
    params = {"token": api_key}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("balance")
    except httpx.HTTPError:
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
