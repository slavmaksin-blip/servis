"""
MAILBUY API client.

Base URL : https://mailbuy.ru/api/v1
Auth     : Bearer token in the ``Authorization`` header.

All public functions return a dict and never raise — any exception is caught
and reported via the ``success`` flag and ``error`` key.

Endpoints used
--------------
GET  /domains          – list available domains with prices
POST /buy              – purchase a new mailbox on the given domain
POST /messages         – fetch inbox messages for a mailbox
POST /refresh          – refresh / ping mailbox status
POST /recreate         – delete current mailbox and create a new one

Response status values (from API documentation)
------------------------------------------------
"ok"     – operation succeeded
"error"  – operation failed (see "message" field)
"""

import httpx
from typing import Optional

MAILBUY_BASE_URL = "https://mailbuy.ru/api/v1"


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


async def get_domains(api_key: str) -> list[dict]:
    """
    Fetch available email domains and their prices.

    Returns a list of dicts::

        [{"domain": str, "price": float}, ...]

    Returns an empty list on any error.
    """
    url = f"{MAILBUY_BASE_URL}/domains"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=_headers(api_key))
            response.raise_for_status()
            data = response.json()
            raw_list = data if isinstance(data, list) else data.get("domains", [])
            return [
                {
                    "domain": d.get("domain") or d.get("name", ""),
                    "price": float(d.get("price", 0)),
                }
                for d in raw_list
                if d.get("domain") or d.get("name")
            ]
    except httpx.HTTPStatusError:
        return []
    except httpx.HTTPError:
        return []
    except Exception:
        return []


async def buy_email(api_key: str, domain: str) -> dict:
    """
    Purchase a new mailbox on *domain*.

    Returns::

        {
            "success":  bool,
            "email":    str,
            "password": str,
            "link":     str,
            "status":   str,
            "error":    str | None,
            "raw":      dict,
        }
    """
    url = f"{MAILBUY_BASE_URL}/buy"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                url,
                headers=_headers(api_key),
                json={"domain": domain},
            )
            response.raise_for_status()
            data = response.json()
            status = data.get("status", "unknown")
            success = status == "ok" or data.get("success", False)
            return {
                "success": success,
                "email": data.get("email", ""),
                "password": data.get("password", ""),
                "link": data.get("link", ""),
                "status": status,
                "error": data.get("message") if not success else None,
                "raw": data,
            }
    except httpx.HTTPStatusError as exc:
        return {
            "success": False,
            "email": "",
            "password": "",
            "link": "",
            "status": f"HTTP {exc.response.status_code}",
            "error": str(exc),
            "raw": {},
        }
    except httpx.HTTPError as exc:
        return {
            "success": False,
            "email": "",
            "password": "",
            "link": "",
            "status": "connection_error",
            "error": str(exc),
            "raw": {},
        }
    except Exception as exc:
        return {
            "success": False,
            "email": "",
            "password": "",
            "link": "",
            "status": "unexpected_error",
            "error": str(exc),
            "raw": {},
        }


async def get_email_messages(api_key: str, email: str) -> dict:
    """
    Fetch inbox messages for *email*.

    Returns::

        {
            "success":  bool,
            "messages": list,
            "error":    str | None,
            "raw":      dict,
        }
    """
    url = f"{MAILBUY_BASE_URL}/messages"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                url,
                headers=_headers(api_key),
                json={"email": email},
            )
            response.raise_for_status()
            data = response.json()
            messages = data.get("messages", data if isinstance(data, list) else [])
            return {
                "success": True,
                "messages": messages,
                "error": None,
                "raw": data,
            }
    except httpx.HTTPStatusError as exc:
        return {
            "success": False,
            "messages": [],
            "error": f"HTTP {exc.response.status_code}: {exc}",
            "raw": {},
        }
    except httpx.HTTPError as exc:
        return {
            "success": False,
            "messages": [],
            "error": str(exc),
            "raw": {},
        }
    except Exception as exc:
        return {
            "success": False,
            "messages": [],
            "error": str(exc),
            "raw": {},
        }


async def refresh_email(api_key: str, email: str) -> dict:
    """
    Refresh / ping mailbox status.

    Returns::

        {"success": bool, "status": str, "error": str | None, "raw": dict}
    """
    url = f"{MAILBUY_BASE_URL}/refresh"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                url,
                headers=_headers(api_key),
                json={"email": email},
            )
            response.raise_for_status()
            data = response.json()
            status = data.get("status", "ok")
            success = status == "ok" or data.get("success", True)
            return {
                "success": success,
                "status": status,
                "error": data.get("message") if not success else None,
                "raw": data,
            }
    except httpx.HTTPStatusError as exc:
        return {
            "success": False,
            "status": f"HTTP {exc.response.status_code}",
            "error": str(exc),
            "raw": {},
        }
    except httpx.HTTPError as exc:
        return {
            "success": False,
            "status": "connection_error",
            "error": str(exc),
            "raw": {},
        }
    except Exception as exc:
        return {
            "success": False,
            "status": "unexpected_error",
            "error": str(exc),
            "raw": {},
        }


async def recreate_email(api_key: str, email: str, domain: str) -> dict:
    """
    Delete the current mailbox and create a new one on the same domain.

    Returns the same shape as :func:`buy_email`.
    """
    url = f"{MAILBUY_BASE_URL}/recreate"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                url,
                headers=_headers(api_key),
                json={"email": email, "domain": domain},
            )
            response.raise_for_status()
            data = response.json()
            status = data.get("status", "unknown")
            success = status == "ok" or data.get("success", False)
            return {
                "success": success,
                "email": data.get("email", ""),
                "password": data.get("password", ""),
                "link": data.get("link", ""),
                "status": status,
                "error": data.get("message") if not success else None,
                "raw": data,
            }
    except httpx.HTTPStatusError as exc:
        return {
            "success": False,
            "email": "",
            "password": "",
            "link": "",
            "status": f"HTTP {exc.response.status_code}",
            "error": str(exc),
            "raw": {},
        }
    except httpx.HTTPError as exc:
        return {
            "success": False,
            "email": "",
            "password": "",
            "link": "",
            "status": "connection_error",
            "error": str(exc),
            "raw": {},
        }
    except Exception as exc:
        return {
            "success": False,
            "email": "",
            "password": "",
            "link": "",
            "status": "unexpected_error",
            "error": str(exc),
            "raw": {},
        }
