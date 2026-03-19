"""
API clients for external services.

SSL notes:
- ssl=False disables certificate verification (workaround for servers with
  misconfigured or self-signed certificates).
- A ClientTimeout is set on every session to prevent hung requests.
- All network calls are wrapped in try/except with retry logic.
"""

import asyncio
import logging
from typing import Any

import aiohttp

from config import (
    MAILBUY_API_KEY,
    MAILBUY_API_URL,
    SMSSEND_API_KEY,
    SMSSEND_API_URL,
)

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30)
_MAX_RETRIES = 3
_RETRY_DELAY = 2.0  # seconds between retries


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _request(
    method: str,
    url: str,
    *,
    retries: int = _MAX_RETRIES,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """
    Generic HTTP request helper with retry logic and SSL verification disabled.

    Parameters
    ----------
    method:
        HTTP method (``'GET'``, ``'POST'``, …).
    url:
        Full request URL.
    retries:
        Number of attempts before giving up.
    **kwargs:
        Extra keyword arguments forwarded to :meth:`aiohttp.ClientSession.request`.

    Returns
    -------
    Parsed JSON response as a dict, or ``None`` on permanent failure.
    """
    kwargs.setdefault("ssl", False)  # disable SSL verification
    kwargs.setdefault("timeout", _DEFAULT_TIMEOUT)

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for attempt in range(1, retries + 1):
            try:
                logger.debug("Request %s %s (attempt %d/%d)", method, url, attempt, retries)
                async with session.request(method, url, **kwargs) as resp:
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
                    logger.debug("Response from %s: %s", url, data)
                    return data
            except aiohttp.ClientResponseError as exc:
                logger.warning(
                    "HTTP error on %s %s (attempt %d/%d): %s %s",
                    method, url, attempt, retries, exc.status, exc.message,
                )
                if exc.status < 500:
                    # 4xx errors won't be fixed by retrying
                    return None
            except (aiohttp.ClientSSLError, aiohttp.ClientConnectorError) as exc:
                logger.warning(
                    "Connection/SSL error on %s %s (attempt %d/%d): %s",
                    method, url, attempt, retries, exc,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Timeout on %s %s (attempt %d/%d)",
                    method, url, attempt, retries,
                )
            except (aiohttp.ClientError, OSError) as exc:
                logger.error(
                    "Unexpected error on %s %s (attempt %d/%d): %s",
                    method, url, attempt, retries, exc,
                    exc_info=True,
                )
                return None

            if attempt < retries:
                await asyncio.sleep(_RETRY_DELAY * attempt)

    logger.error("All %d attempts failed for %s %s", retries, method, url)
    return None


# ---------------------------------------------------------------------------
# SMSSend API
# ---------------------------------------------------------------------------

class SMSSendAPI:
    """Client for the SMSSEND SMS-sending service."""

    def __init__(self, api_key: str = SMSSEND_API_KEY, base_url: str = SMSSEND_API_URL) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def send_sms(self, phone: str, message: str) -> dict[str, Any] | None:
        """
        Send an SMS message.

        Parameters
        ----------
        phone:
            Recipient phone number (international format, e.g. ``+79001234567``).
        message:
            Text of the message.

        Returns
        -------
        API response dict on success, or ``None`` on failure.
        """
        url = f"{self.base_url}/send"
        payload = {
            "api_key": self.api_key,
            "phone": phone,
            "message": message,
        }
        logger.info("Sending SMS to %s via SMSSend", phone)
        result = await _request("POST", url, json=payload)
        if result is None:
            logger.error("SMSSend: failed to send SMS to %s", phone)
        return result

    async def get_balance(self) -> float | None:
        """
        Retrieve the current account balance.

        Returns
        -------
        Balance as a float, or ``None`` on failure.
        """
        url = f"{self.base_url}/balance"
        params = {"api_key": self.api_key}
        logger.info("Fetching SMSSend account balance")
        result = await _request("GET", url, params=params)
        if result is None:
            logger.error("SMSSend: failed to fetch balance")
            return None
        return result.get("balance")

    async def check_status(self, message_id: str) -> dict[str, Any] | None:
        """
        Check the delivery status of a previously sent message.

        Parameters
        ----------
        message_id:
            ID returned by :meth:`send_sms`.

        Returns
        -------
        Status dict, or ``None`` on failure.
        """
        url = f"{self.base_url}/status"
        params = {"api_key": self.api_key, "id": message_id}
        logger.info("Checking SMSSend status for message %s", message_id)
        result = await _request("GET", url, params=params)
        if result is None:
            logger.error("SMSSend: failed to check status for message %s", message_id)
        return result


# ---------------------------------------------------------------------------
# MailBuy API
# ---------------------------------------------------------------------------

class MailBuyAPI:
    """Client for the MailBuy temporary-email service."""

    def __init__(self, api_key: str = MAILBUY_API_KEY, base_url: str = MAILBUY_API_URL) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def create_mailbox(self) -> dict[str, Any] | None:
        """
        Create a new temporary mailbox.

        Returns
        -------
        Mailbox details (address, id, …) on success, or ``None`` on failure.
        """
        url = f"{self.base_url}/mailbox"
        logger.info("Creating MailBuy mailbox")
        result = await _request("POST", url, headers=self._headers())
        if result is None:
            logger.error("MailBuy: failed to create mailbox")
        return result

    async def get_messages(self, mailbox_id: str) -> list[dict[str, Any]] | None:
        """
        Retrieve messages for a mailbox.

        Parameters
        ----------
        mailbox_id:
            ID of the mailbox to query.

        Returns
        -------
        List of message dicts, or ``None`` on failure.
        """
        url = f"{self.base_url}/mailbox/{mailbox_id}/messages"
        logger.info("Fetching MailBuy messages for mailbox %s", mailbox_id)
        result = await _request("GET", url, headers=self._headers())
        if result is None:
            logger.error("MailBuy: failed to fetch messages for mailbox %s", mailbox_id)
            return None
        return result if isinstance(result, list) else result.get("messages")

    async def get_message(self, mailbox_id: str, message_id: str) -> dict[str, Any] | None:
        """
        Retrieve a single message.

        Parameters
        ----------
        mailbox_id:
            ID of the mailbox.
        message_id:
            ID of the message to retrieve.

        Returns
        -------
        Message dict, or ``None`` on failure.
        """
        url = f"{self.base_url}/mailbox/{mailbox_id}/messages/{message_id}"
        logger.info("Fetching MailBuy message %s from mailbox %s", message_id, mailbox_id)
        result = await _request("GET", url, headers=self._headers())
        if result is None:
            logger.error(
                "MailBuy: failed to fetch message %s from mailbox %s",
                message_id, mailbox_id,
            )
        return result

    async def delete_mailbox(self, mailbox_id: str) -> bool:
        """
        Delete a mailbox.

        Parameters
        ----------
        mailbox_id:
            ID of the mailbox to delete.

        Returns
        -------
        ``True`` on success, ``False`` on failure.
        """
        url = f"{self.base_url}/mailbox/{mailbox_id}"
        logger.info("Deleting MailBuy mailbox %s", mailbox_id)
        result = await _request("DELETE", url, headers=self._headers())
        success = result is not None
        if not success:
            logger.error("MailBuy: failed to delete mailbox %s", mailbox_id)
        return success
