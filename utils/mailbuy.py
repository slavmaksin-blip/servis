import httpx
from typing import Optional

MAILBUY_BASE_URL = "https://mailbuy.ru/api/v1"


async def get_domains(api_key: str) -> list[dict]:
    """
    Fetch available email domains and their prices.
    Returns list of dicts: [{domain, price}, ...]
    """
    url = f"{MAILBUY_BASE_URL}/domains"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            domains = data.get("domains", data if isinstance(data, list) else [])
            return [
                {"domain": d.get("domain", d.get("name", "")), "price": float(d.get("price", 0))}
                for d in domains
            ]
    except httpx.HTTPError:
        return []


async def buy_email(api_key: str, domain: str) -> dict:
    """
    Purchase an email on the given domain.
    Returns: {success, email, password, link, status}
    """
    url = f"{MAILBUY_BASE_URL}/buy"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"domain": domain}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return {
                "success": data.get("status") == "ok" or data.get("success", False),
                "email": data.get("email", ""),
                "password": data.get("password", ""),
                "link": data.get("link", ""),
                "status": data.get("status", "unknown"),
                "raw": data,
            }
    except httpx.HTTPError as exc:
        return {
            "success": False,
            "email": "",
            "password": "",
            "link": "",
            "status": f"HTTP error: {exc}",
            "raw": {},
        }


async def refresh_email(api_key: str, email: str) -> dict:
    """
    Refresh/check email status.
    Returns: {success, status, raw}
    """
    url = f"{MAILBUY_BASE_URL}/refresh"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"email": email}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return {"success": True, "status": data.get("status", "ok"), "raw": data}
    except httpx.HTTPError as exc:
        return {"success": False, "status": f"HTTP error: {exc}", "raw": {}}


async def get_email_message(api_key: str, email: str) -> dict:
    """
    Get messages for an email.
    Returns: {success, messages, raw}
    """
    url = f"{MAILBUY_BASE_URL}/messages"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"email": email}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return {"success": True, "messages": data.get("messages", []), "raw": data}
    except httpx.HTTPError as exc:
        return {"success": False, "messages": [], "raw": {}, "error": str(exc)}


async def recreate_email(api_key: str, email: str, domain: str) -> dict:
    """
    Recreate (delete and buy new) email on same domain.
    """
    url = f"{MAILBUY_BASE_URL}/recreate"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"email": email, "domain": domain}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return {
                "success": data.get("status") == "ok" or data.get("success", False),
                "email": data.get("email", ""),
                "password": data.get("password", ""),
                "link": data.get("link", ""),
                "status": data.get("status", "unknown"),
                "raw": data,
            }
    except httpx.HTTPError as exc:
        return {
            "success": False,
            "email": "",
            "password": "",
            "link": "",
            "status": f"HTTP error: {exc}",
            "raw": {},
        }
