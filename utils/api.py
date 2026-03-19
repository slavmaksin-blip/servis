"""
API clients for SMSSend and MailBuy (AnyMessage Shop) services.

SMSSEND API: http://47.236.91.242:20003
MailBuy API:  https://api.anymessage.shop
"""

import logging
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SMSSEND_ERROR_CODES: Dict[int, str] = {
    0: "Успешно",
    -1: "Ошибка аутентификации",
    -2: "Доступ ограничен по IP",
    -3: "SMS содержит запрещённые слова",
    -4: "Текст SMS пуст",
    -5: "Текст SMS слишком длинный",
    -6: "Не шаблонная SMS",
    -7: "Превышено число получателей",
    -8: "Список номеров пуст",
    -9: "Некорректный номер",
    -10: "Недостаточно средств на балансе канала",
    -11: "Неверное время отправки",
    -12: "Ошибка пакетной отправки — обратитесь к администратору",
    -13: "Пользователь заблокирован",
    -14: "Некорректный источник номеров",
    -15: "Имя задачи некорректно (пустое или длиннее 64 символов)",
    -16: "Тип задачи SMS некорректен",
    -17: "Прочие ошибки",
}

_SMSSEND_SEND_STATUS: Dict[int, str] = {
    0: "Отправлено успешно",
    1: "Не отправлено",
    2: "Отправляется",
}

_SMSSEND_DELIVER_STATUS: Dict[int, str] = {
    0: "Доставка не требуется",
    1: "Отправлено, ожидает доставки",
    2: "Ошибка доставки",
    3: "Доставлено успешно",
    4: "Таймаут доставки",
    5: "Другой неизвестный статус",
}

SMSSEND_STATUS_CODES: Dict[int, str] = {
    1001: "NoRoute",
    1002: "NoChannel",
    1003: "NoBalance",
    1004: "Unknown",
    1005: "SendRefuse",
    1006: "SendTimeout",
    1007: "ServerTimeout",
    1008: "SupplierMccMncLimit",
    1009: "ConsumerMccMncLimit",
    1010: "NoSupplier",
    1011: "BlackNumber",
    1012: "SensitiveWords",
    1013: "DailyLimit",
    1014: "DestinationMccMncLimit",
    1016: "SMSTemplateLimit",
    1017: "SupplierNoBalance",
    1018: "UserProfitLimit",
    1019: "ChannelProfitLimit",
    1020: "MccNumberLengthLimit",
    1021: "JobNotFound",
    1022: "ChinaSMSLimit",
    1023: "RouteMccMncLimit",
}


def _build_session(retries: int = 3, backoff: float = 0.5) -> requests.Session:
    """Return a requests.Session with retry/backoff logic."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# ---------------------------------------------------------------------------
# SMSSend API
# ---------------------------------------------------------------------------

class SMSSendAPI:
    """
    Client for the SMSSend HTTP API.

    Base URL: http://47.236.91.242:20003
    Docs: SMSSEND.pdf
    """

    BASE_URL = "http://47.236.91.242:20003"
    TIMEOUT = 30

    def __init__(self, account: str, password: str) -> None:
        self.account = account
        self.password = password
        self._session = _build_session()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _common_params(self) -> Dict[str, Any]:
        return {"account": self.account, "password": self.password}

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        all_params = {**self._common_params(), **(params or {})}
        try:
            response = self._session.get(url, params=all_params, timeout=self.TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.SSLError as exc:
            logger.error("SSL error contacting SMSSend: %s", exc)
            return {"status": -99, "error": f"SSL error: {exc}"}
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error contacting SMSSend: %s", exc)
            return {"status": -99, "error": f"Connection error: {exc}"}
        except requests.exceptions.Timeout as exc:
            logger.error("Timeout contacting SMSSend: %s", exc)
            return {"status": -99, "error": f"Timeout: {exc}"}
        except Exception as exc:
            logger.error("Unexpected error contacting SMSSend: %s", exc)
            return {"status": -99, "error": str(exc)}

    def _post(self, endpoint: str, body: Dict) -> Dict:
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json;charset=utf-8"}
        try:
            response = self._session.post(
                url, json=body, headers=headers, timeout=self.TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.SSLError as exc:
            logger.error("SSL error contacting SMSSend: %s", exc)
            return {"status": -99, "error": f"SSL error: {exc}"}
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error contacting SMSSend: %s", exc)
            return {"status": -99, "error": f"Connection error: {exc}"}
        except requests.exceptions.Timeout as exc:
            logger.error("Timeout contacting SMSSend: %s", exc)
            return {"status": -99, "error": f"Timeout: {exc}"}
        except Exception as exc:
            logger.error("Unexpected error contacting SMSSend: %s", exc)
            return {"status": -99, "error": str(exc)}

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def get_balance(self) -> Dict:
        """
        GET /getbalance — Retrieve account balance.

        Returns dict with keys:
            status  (int)  : 0 = OK, negative = error code
            balance (str)  : actual balance
            gift    (str)  : bonus/gift balance
        """
        result = self._get("getbalance")
        logger.debug("SMSSend getbalance: %s", result)
        return result

    def send_sms(
        self,
        numbers: str,
        content: str,
        smstype: int = 0,
        mmstitle: str = "",
        sender: str = "",
        sendtime: str = "",
    ) -> Dict:
        """
        POST /sendsms — Send an SMS message to one or more numbers.

        Parameters
        ----------
        numbers  : Comma-separated phone numbers (up to 10 000 via POST).
        content  : Message text (max 1 024 chars).
        smstype  : 0 = SMS (default), 1 = MMS.
        mmstitle : MMS title (required when smstype=1).
        sender   : Sender ID string (optional).
        sendtime : Scheduled send time "YYYYMMDDHHmmss" (empty = send now).

        Returns dict with keys:
            status  (int) : 0 = submitted OK, negative = error code
            success (int) : number of successfully queued messages
            fail    (int) : number of failures
            array   (list): [[number, sms_id], ...] for successful submissions
        """
        body: Dict[str, Any] = {
            "account": self.account,
            "password": self.password,
            "numbers": numbers,
            "content": content,
            "smstype": smstype,
        }
        if mmstitle:
            body["mmstitle"] = mmstitle
        if sender:
            body["sender"] = sender
        if sendtime:
            body["sendtime"] = sendtime

        result = self._post("sendsms", body)
        logger.debug("SMSSend sendsms: %s", result)
        return result

    def send_sms_batch(self, smsarray: List[Dict]) -> Dict:
        """
        POST /sendsms — Send multiple SMS messages in a single batch call.

        Each element of smsarray should be a dict with keys:
            content, smstype, numbers  (required)
            mmstitle, sender           (optional)

        Returns same structure as send_sms().
        """
        body: Dict[str, Any] = {
            "account": self.account,
            "password": self.password,
            "smsarray": smsarray,
        }
        result = self._post("sendsms", body)
        logger.debug("SMSSend sendsms batch: %s", result)
        return result

    def get_report(self, ids: str) -> Dict:
        """
        GET /getreport — Query SMS delivery status for one or more SMS IDs.

        Parameters
        ----------
        ids : Comma-separated SMS IDs returned by send_sms() (up to 200).

        Returns dict with keys:
            status        (int)
            success       (int) : delivered successfully
            fail          (int) : delivery failed
            unsent        (int) : not yet sent
            sending       (int) : currently sending
            nofound       (int) : ID not found
            array         (list): [[id, number, sendtime, send_status, deliver_status], ...]
        """
        result = self._get("getreport", {"ids": ids})
        logger.debug("SMSSend getreport: %s", result)
        return result

    def get_sms(self, start_time: Optional[int] = None) -> Dict:
        """
        GET /getsms — Retrieve incoming SMS messages (up to 50 per call).

        Parameters
        ----------
        start_time : Unix timestamp; query messages received from this time.

        Returns dict with keys:
            status (int)
            cnt    (int) : number of messages returned
            array  (list): [[id, number, sendtime, base64_content], ...]

        Note: message content is Base64-encoded UTF-8.
        """
        params: Dict[str, Any] = {}
        if start_time is not None:
            params["start_time"] = start_time
        result = self._get("getsms", params)
        logger.debug("SMSSend getsms: %s", result)
        return result

    def create_sms_job(
        self,
        job: str,
        numbers: str,
        content: str,
        jobtype: int = 0,
        numbersrc: int = 0,
        smstype: int = 0,
        mmstitle: str = "",
        sender_id: str = "",
        period: Optional[int] = None,
        interval: Optional[int] = None,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        day: Optional[int] = None,
        week: Optional[int] = None,
        month: Optional[int] = None,
        planstarttm: Optional[int] = None,
        planendtm: Optional[int] = None,
        retry: int = 0,
        flash: int = 0,
    ) -> Dict:
        """
        POST /smsjob — Create a scheduled or immediate SMS job.

        Parameters
        ----------
        job      : Task name (max 64 chars).
        numbers  : Comma-separated numbers or a URL to an XLS file.
        content  : SMS content.
        jobtype  : 0=immediately, 1=timing, 2=interval, 3=daily, 4=weekly, 5=monthly.
        numbersrc: 0=numbers field contains phone numbers,
                   1=numbers field contains a URL to an XLS file.
        ...

        Returns dict with keys:
            status (int) : 0 = OK
            jobid  (int) : ID of the created job
        """
        body: Dict[str, Any] = {
            "account": self.account,
            "password": self.password,
            "job": job,
            "numbers": numbers,
            "content": content,
            "jobtype": jobtype,
            "numbersrc": numbersrc,
            "smstype": smstype,
            "retry": retry,
            "flash": flash,
        }
        if mmstitle:
            body["mmstitle"] = mmstitle
        if sender_id:
            body["senderid"] = sender_id
        for key, value in [
            ("period", period),
            ("interval", interval),
            ("hour", hour),
            ("min", minute),
            ("day", day),
            ("week", week),
            ("mon", month),
            ("planstarttm", planstarttm),
            ("planendtm", planendtm),
        ]:
            if value is not None:
                body[key] = value

        result = self._post("smsjob", body)
        logger.debug("SMSSend smsjob: %s", result)
        return result

    @staticmethod
    def describe_status(status_code: int) -> str:
        """Return a human-readable description for a status/error code."""
        if status_code in _SMSSEND_ERROR_CODES:
            return _SMSSEND_ERROR_CODES[status_code]
        if status_code in SMSSEND_STATUS_CODES:
            return SMSSEND_STATUS_CODES[status_code]
        return f"Неизвестный код: {status_code}"

    @staticmethod
    def describe_send_status(code: int) -> str:
        return _SMSSEND_SEND_STATUS.get(code, f"Неизвестно ({code})")

    @staticmethod
    def describe_deliver_status(code: int) -> str:
        return _SMSSEND_DELIVER_STATUS.get(code, f"Неизвестно ({code})")


# ---------------------------------------------------------------------------
# MailBuy (AnyMessage Shop) API
# ---------------------------------------------------------------------------

_MAILBUY_ERROR_MESSAGES: Dict[str, str] = {
    "token": "Неверный токен",
    "site": "Некорректный сайт",
    "domain": "Некорректный домен",
    "no emails": "Нет доступных почтовых ящиков",
    "no balance": "Недостаточно средств на балансе",
    "wait message": "Письмо ещё не пришло",
    "activation canceled": "Активация отменена",
    "no activation": "Активация не найдена",
    "activation already canceled": "Активация уже была отменена",
    "email banned": "Почтовый ящик заблокирован",
}


class MailBuyAPI:
    """
    Client for the AnyMessage Shop email API.

    Base URL: https://api.anymessage.shop
    Docs: mailbuy.pdf
    """

    BASE_URL = "https://api.anymessage.shop"
    TIMEOUT = 30

    def __init__(self, token: str) -> None:
        self.token = token
        self._session = _build_session()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        all_params = {"token": self.token, **(params or {})}
        try:
            response = self._session.get(
                url, params=all_params, timeout=self.TIMEOUT, verify=True
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.SSLError as exc:
            logger.error("SSL error contacting MailBuy: %s", exc)
            return {"status": "error", "value": f"SSL error: {exc}"}
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error contacting MailBuy: %s", exc)
            return {"status": "error", "value": f"Connection error: {exc}"}
        except requests.exceptions.Timeout as exc:
            logger.error("Timeout contacting MailBuy: %s", exc)
            return {"status": "error", "value": f"Timeout: {exc}"}
        except Exception as exc:
            logger.error("Unexpected error contacting MailBuy: %s", exc)
            return {"status": "error", "value": str(exc)}

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def get_balance(self) -> Dict:
        """
        GET /user/balance — Retrieve account balance.

        Returns dict with keys:
            status  (str) : "success" or "error"
            balance (str) : account balance (on success)
            value   (str) : error description (on error)
        """
        result = self._get("user/balance")
        logger.debug("MailBuy get_balance: %s", result)
        return result

    def get_email_quantity(self, site: str) -> Dict:
        """
        GET /email/quantity — List available email counts and prices per domain.

        Parameters
        ----------
        site : Target website, e.g. "instagram.com".

        Returns dict with keys:
            status (str)  : "success" or "error"
            data   (dict) : {domain: {count, price}, ...} on success
            value  (str)  : error description on error
        """
        result = self._get("email/quantity", {"site": site})
        logger.debug("MailBuy get_email_quantity [%s]: %s", site, result)
        return result

    def order_email(
        self,
        site: str,
        domain: str,
        regex: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> Dict:
        """
        GET /email/order — Order an email address for a specific site.

        Parameters
        ----------
        site    : Target website, e.g. "instagram.com".
        domain  : Desired email domain, e.g. "gmx.com" or aggregator keyword
                  like "mailcom,gmx,hotmail,outlook".
        regex   : Optional regex for custom message parsing.
        subject : Optional email subject filter.

        Returns dict with keys:
            status (str) : "success" or "error"
            id     (str) : activation ID (on success)
            email  (str) : assigned email address (on success)
            value  (str) : error description (on error)
        """
        params: Dict[str, Any] = {"site": site, "domain": domain}
        if regex:
            params["regex"] = regex
        if subject:
            params["subject"] = subject
        result = self._get("email/order", params)
        logger.debug("MailBuy order_email [%s/%s]: %s", site, domain, result)
        return result

    def get_message(self, activation_id: str, preview: bool = False) -> Dict:
        """
        GET /email/getmessage — Poll for an incoming message for an activation.

        Parameters
        ----------
        activation_id : The ID returned by order_email() or reorder_email().
        preview       : If True, returns the message body as HTML.

        Returns dict with keys:
            status (str)   : "success" or "error"
            value  (str)   : OTP / activation code (on success) OR error text
            message (str)  : HTML email body (on success, if preview=True)
        """
        params: Dict[str, Any] = {"id": activation_id}
        if preview:
            params["preview"] = 1
        result = self._get("email/getmessage", params)
        logger.debug("MailBuy get_message [id=%s]: %s", activation_id, result)
        return result

    def reorder_email(
        self,
        activation_id: Optional[str] = None,
        email: Optional[str] = None,
        site: Optional[str] = None,
        regex: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> Dict:
        """
        GET /email/reorder — Re-order (re-use) an existing email activation.

        You must provide either:
            activation_id          — to reorder by existing ID, OR
            email + site           — to reorder by email address and site.

        Returns same structure as order_email().
        """
        params: Dict[str, Any] = {}
        if activation_id:
            params["id"] = activation_id
        elif email and site:
            params["email"] = email
            params["site"] = site
        else:
            raise ValueError(
                "reorder_email() requires either activation_id OR (email and site)."
            )
        if regex:
            params["regex"] = regex
        if subject:
            params["subject"] = subject

        result = self._get("email/reorder", params)
        logger.debug("MailBuy reorder_email: %s", result)
        return result

    def cancel_email(self, activation_id: str) -> Dict:
        """
        GET /email/cancel — Cancel an email activation.

        Parameters
        ----------
        activation_id : The activation ID to cancel.

        Returns dict with keys:
            status (str) : "success" or "error"
            value  (str) : "activation canceled" on success, error text on error
        """
        result = self._get("email/cancel", {"id": activation_id})
        logger.debug("MailBuy cancel_email [id=%s]: %s", activation_id, result)
        return result

    @staticmethod
    def describe_error(value: str) -> str:
        """Return a human-readable Russian description of a MailBuy error value."""
        return _MAILBUY_ERROR_MESSAGES.get(value, f"Неизвестная ошибка: {value}")

    def wait_for_message(
        self,
        activation_id: str,
        max_wait: int = 120,
        poll_interval: int = 5,
        preview: bool = False,
    ) -> Dict:
        """
        Poll get_message() until a message arrives or max_wait seconds elapse.

        Parameters
        ----------
        activation_id : Activation ID from order_email().
        max_wait      : Maximum seconds to wait (default 120).
        poll_interval : Seconds between polls (default 5).
        preview       : Pass through to get_message().

        Returns the last response dict from get_message().
        """
        deadline = time.monotonic() + max_wait
        while time.monotonic() < deadline:
            result = self.get_message(activation_id, preview=preview)
            if result.get("status") == "success":
                return result
            error_val = result.get("value", "")
            if error_val != "wait message":
                # Fatal error — return immediately
                return result
            remaining = deadline - time.monotonic()
            sleep_time = min(poll_interval, remaining)
            if sleep_time <= 0:
                break
            time.sleep(sleep_time)
        return {"status": "error", "value": "wait message"}