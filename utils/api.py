import aiohttp
import ssl
from typing import Optional, Dict, Any
from config import (
    SMSSEND_API_URL,
    SMSSEND_ACCOUNT,
    SMSSEND_PASSWORD,
    MAILBUY_API_URL,
    MAILBUY_TOKEN,
)
import logging

logger = logging.getLogger(__name__)

# SSL context that skips certificate verification for hosts with invalid certs
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


class SMSSendAPI:
    @staticmethod
    async def send_sms(number: str, message: str, sender: str) -> Dict[str, Any]:
        """Отправить SMS через SMSSEND API"""
        try:
            url = f"{SMSSEND_API_URL}/sendsms"
            params = {
                "account": SMSSEND_ACCOUNT,
                "password": SMSSEND_PASSWORD,
                "numbers": number,
                "content": message,
                "sender": sender,
                "smstype": 0,
            }

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    url, params=params, timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        success = data.get("status") == 0
                        return {
                            "success": success,
                            "status": data.get("status"),
                            "message": (
                                "✅ SMS отправлено успешно"
                                if success
                                else "❌ Ошибка отправки"
                            ),
                            "data": data,
                        }
                    return {
                        "success": False,
                        "message": f"❌ Ошибка сервера: {response.status}",
                        "data": None,
                    }
        except aiohttp.ClientSSLError as e:
            logger.error(f"SSL Error (send_sms): {e}")
            return {"success": False, "message": f"❌ Ошибка SSL: {e}", "data": None}
        except aiohttp.ClientError as e:
            logger.error(f"Client Error (send_sms): {e}")
            return {
                "success": False,
                "message": f"❌ Ошибка подключения: {e}",
                "data": None,
            }
        except Exception as e:
            logger.error(f"Unexpected error (send_sms): {e}")
            return {"success": False, "message": f"❌ Ошибка: {e}", "data": None}

    @staticmethod
    async def get_balance() -> Dict[str, Any]:
        """Получить баланс счёта"""
        try:
            url = f"{SMSSEND_API_URL}/getbalance"
            params = {
                "account": SMSSEND_ACCOUNT,
                "password": SMSSEND_PASSWORD,
            }

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    url, params=params, timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": data.get("status") == 0,
                            "balance": float(data.get("balance", 0)),
                            "gift": float(data.get("gift", 0)),
                            "data": data,
                        }
        except Exception as e:
            logger.error(f"Balance error: {e}")
        return {"success": False, "balance": 0.0, "gift": 0.0, "data": None}


class MailBuyAPI:
    @staticmethod
    async def _get(path: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Internal helper for GET requests to the MailBuy API."""
        params["token"] = MAILBUY_TOKEN
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    f"{MAILBUY_API_URL}{path}",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            logger.error(f"MailBuyAPI request error ({path}): {e}")
        return None

    @staticmethod
    async def order_email(
        site: str, domain: str, regex: str = None
    ) -> Dict[str, Any]:
        """Заказать почту"""
        params: Dict[str, Any] = {"site": site, "domain": domain}
        if regex:
            params["regex"] = regex

        data = await MailBuyAPI._get("/email/order", params)
        if data:
            return {
                "success": data.get("status") == "success",
                "id": data.get("id"),
                "email": data.get("email"),
                "message": data.get("status"),
                "data": data,
            }
        return {
            "success": False,
            "message": "❌ Ошибка подключения к MailBuy API",
            "data": None,
        }

    @staticmethod
    async def get_message(
        activation_id: str, preview: bool = False
    ) -> Dict[str, Any]:
        """Получить письмо"""
        params: Dict[str, Any] = {
            "id": activation_id,
            "preview": 1 if preview else 0,
        }

        data = await MailBuyAPI._get("/email/getmessage", params)
        if data:
            return {
                "success": data.get("status") == "success",
                "status": data.get("status"),
                "value": data.get("value"),
                "message": (
                    data.get("message")
                    if data.get("status") == "success"
                    else data.get("value")
                ),
                "data": data,
            }
        return {
            "success": False,
            "message": "❌ Ошибка подключения к MailBuy API",
            "data": None,
        }

    @staticmethod
    async def reorder_email(
        activation_id: str = None, email: str = None, site: str = None
    ) -> Dict[str, Any]:
        """Переделать почту"""
        params: Dict[str, Any] = {}
        if activation_id:
            params["id"] = activation_id
        elif email and site:
            params["email"] = email
            params["site"] = site

        data = await MailBuyAPI._get("/email/reorder", params)
        if data:
            return {
                "success": data.get("status") == "success",
                "message": data.get("status"),
                "data": data,
            }
        return {
            "success": False,
            "message": "❌ Ошибка подключения к MailBuy API",
            "data": None,
        }

    @staticmethod
    async def cancel_email(activation_id: str) -> Dict[str, Any]:
        """Отменить почту"""
        data = await MailBuyAPI._get("/email/cancel", {"id": activation_id})
        if data:
            return {
                "success": data.get("status") == "success",
                "message": data.get("status"),
                "data": data,
            }
        return {
            "success": False,
            "message": "❌ Ошибка подключения к MailBuy API",
            "data": None,
        }
