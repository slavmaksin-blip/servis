import httpx
from typing import Optional

CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"
XROCKET_API_URL = "https://pay.xrocket.tg/api"


async def create_cryptobot_invoice(
    token: str, amount: float, description: str, payload: str = ""
) -> Optional[str]:
    """
    Create a CryptoBot invoice and return the pay URL.
    """
    url = f"{CRYPTOBOT_API_URL}/createInvoice"
    headers = {"Crypto-Pay-API-Token": token}
    data = {
        "asset": "USDT",
        "amount": str(round(amount, 2)),
        "description": description,
        "payload": payload,
        "allow_comments": False,
        "allow_anonymous": False,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            if result.get("ok"):
                invoice = result["result"]
                return invoice.get("pay_url") or invoice.get("bot_invoice_url")
            return None
    except httpx.HTTPError:
        return None


async def create_xrocket_invoice(
    token: str, amount: float, description: str
) -> Optional[str]:
    """
    Create an xRocket invoice and return the pay URL.
    """
    url = f"{XROCKET_API_URL}/tg-invoices"
    headers = {
        "Rocket-Pay-Key": token,
        "Content-Type": "application/json",
    }
    data = {
        "amount": round(amount, 2),
        "currency": "USDT",
        "description": description,
        "hiddenMessage": "Спасибо за оплату!",
        "callbackUrl": "",
        "payload": "",
        "expiredIn": 3600,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            if result.get("success"):
                return result.get("data", {}).get("link")
            return None
    except httpx.HTTPError:
        return None
