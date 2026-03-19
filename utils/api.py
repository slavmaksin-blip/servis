import aiohttp
import logging

from config import SMSSEND_ACCOUNT, SMSSEND_PASSWORD, SMSSEND_API_URL, MAILBUY_TOKEN, MAILBUY_API_URL

logger = logging.getLogger(__name__)


class SMSSendAPI:
    """Integration with SMSSEND API."""

    @staticmethod
    async def _request(endpoint: str, params: dict) -> dict:
        params.update({"account": SMSSEND_ACCOUNT, "password": SMSSEND_PASSWORD})
        async with aiohttp.ClientSession() as session:
            async with session.get(
                SMSSEND_API_URL + endpoint, params=params, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                data = await resp.json(content_type=None)
                logger.debug("SMSSendAPI %s → %s", endpoint, data)
                return data

    @staticmethod
    async def send_sms(phone: str, sender: str, text: str) -> dict:
        return await SMSSendAPI._request(
            "send",
            {"recipient": phone, "sender": sender, "message": text},
        )

    @staticmethod
    async def get_balance() -> dict:
        return await SMSSendAPI._request("balance", {})


class MailBuyAPI:
    """Integration with MailBuy API."""

    @staticmethod
    async def _request(method: str, endpoint: str, payload: dict | None = None) -> dict:
        url = f"{MAILBUY_API_URL}/{endpoint}"
        headers = {"Authorization": f"Bearer {MAILBUY_TOKEN}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            if method == "GET":
                async with session.get(url, params=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    data = await resp.json(content_type=None)
            else:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    data = await resp.json(content_type=None)
        logger.debug("MailBuyAPI %s %s → %s", method, endpoint, data)
        return data

    @staticmethod
    async def order_email(domain: str) -> dict:
        return await MailBuyAPI._request("POST", "order", {"domain": domain})

    @staticmethod
    async def get_message(order_id: str) -> list[dict]:
        result = await MailBuyAPI._request("GET", "messages", {"order_id": order_id})
        if isinstance(result, list):
            return result
        return result.get("messages", [])

    @staticmethod
    async def reorder_email(order_id: str) -> dict:
        return await MailBuyAPI._request("POST", "reorder", {"order_id": order_id})

    @staticmethod
    async def cancel_email(order_id: str) -> dict:
        return await MailBuyAPI._request("POST", "cancel", {"order_id": order_id})
