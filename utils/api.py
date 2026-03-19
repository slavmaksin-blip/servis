import aiohttp
import logging

logger = logging.getLogger(__name__)


class SMSSendAPI:
    """Integration with SMSSEND API."""

    def __init__(self, account: str, password: str) -> None:
        self._account = account
        self._password = password
        self._base_url = "https://smssend.ch/api/"

    async def _request(self, method: str, params: dict) -> dict:
        params.update({"account": self._account, "password": self._password})
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self._base_url + method, params=params, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                data = await resp.json(content_type=None)
                logger.debug("SMSSendAPI %s → %s", method, data)
                return data

    async def send_sms(self, phone: str, sender: str, text: str) -> dict:
        return await self._request(
            "send",
            {"recipient": phone, "sender": sender, "message": text},
        )

    async def get_balance(self) -> dict:
        return await self._request("balance", {})


class MailBuyAPI:
    """Integration with MailBuy API."""

    def __init__(self, token: str) -> None:
        self._token = token
        self._base_url = "https://mailbuy.cc/api"
        self._headers = {"Authorization": f"Bearer {token}"}

    async def _request(self, method: str, endpoint: str, payload: dict | None = None) -> dict:
        url = f"{self._base_url}/{endpoint}"
        async with aiohttp.ClientSession(headers=self._headers) as session:
            if method == "GET":
                async with session.get(url, params=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    data = await resp.json(content_type=None)
            else:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    data = await resp.json(content_type=None)
        logger.debug("MailBuyAPI %s %s → %s", method, endpoint, data)
        return data

    async def order_email(self, domain: str) -> dict:
        return await self._request("POST", "order", {"domain": domain})

    async def get_message(self, order_id: str) -> list[dict]:
        result = await self._request("GET", "messages", {"order_id": order_id})
        if isinstance(result, list):
            return result
        return result.get("messages", [])

    async def reorder_email(self, order_id: str) -> dict:
        return await self._request("POST", "reorder", {"order_id": order_id})

    async def cancel_email(self, order_id: str) -> dict:
        return await self._request("POST", "cancel", {"order_id": order_id})
