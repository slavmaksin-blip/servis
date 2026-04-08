# Mensor Partner API — Documentation

**Version:** 1.1  
**Base URL:** `http://<your-server>:<API_PORT>` (default port: `8080`)

---

## Overview

Mensor exposes an HTTP REST API that lets partner bots access the **SMS**, **Mailer**, **Screen**, and **PDF** modules without any rate limits.

All requests (except `/api/v1/ping`) require a valid API key sent in the `X-API-Key` HTTP header.

API keys are managed by the bot administrator via the `/admin` → **🔑 API ключи партнёров** menu.

---

## Authentication

Include the API key as a header in every request:

```
X-API-Key: <your-api-key>
```

| Condition | HTTP Status | Response |
|-----------|-------------|----------|
| Key missing | `401` | `{"ok": false, "error": "Invalid or missing API key"}` |
| Key invalid / revoked | `401` | `{"ok": false, "error": "Invalid or missing API key"}` |
| Key valid | `200` / `2xx` | Endpoint-specific response |

---

## Endpoints

### `GET /api/v1/ping`

Health check. No authentication required.

**Response:**
```json
{
  "ok": true,
  "service": "Mensor API",
  "version": "1.0"
}
```

---

### `POST /api/v1/sms/send`

Send an SMS message via the configured SMS provider (TraffikLink).

**Headers:**
```
Content-Type: application/json
X-API-Key: <your-api-key>
```

**Request body:**
```json
{
  "phone":  "+41791234567",
  "text":   "Your verification code is 1234",
  "sender": "MyBrand"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `phone` | string | ✅ | Recipient phone number with country code prefix (e.g. `+41791234567`) |
| `text` | string | ✅ | SMS text. Maximum **150 characters** |
| `sender` | string | ❌ | Sender ID displayed on the recipient's phone. Maximum **12 characters** |

**Success response (`200`):**
```json
{
  "ok": true,
  "sms_id": "12345678",
  "success": 1
}
```

**Error responses:**

| HTTP | Meaning |
|------|---------|
| `400` | Validation error (missing/invalid fields) |
| `401` | Invalid or missing API key |
| `502` | SMS provider error or unreachable |

**Error body:**
```json
{
  "ok": false,
  "error": "Description of the problem"
}
```

**Example (curl):**
```bash
curl -X POST http://your-server:8080/api/v1/sms/send \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "phone": "+41791234567",
    "text": "Hello from Mensor!",
    "sender": "Mensor"
  }'
```

**Example (Python):**
```python
import httpx

response = httpx.post(
    "http://your-server:8080/api/v1/sms/send",
    headers={"X-API-Key": "your-api-key-here"},
    json={
        "phone": "+41791234567",
        "text": "Hello from Mensor!",
        "sender": "Mensor",
    },
)
data = response.json()
if data["ok"]:
    print("SMS sent, ID:", data["sms_id"])
else:
    print("Error:", data["error"])
```

---

### `POST /api/v1/mail/send`

Send an HTML email via the configured SMTP pool (with automatic SMTP rotation).

**Headers:**
```
Content-Type: application/json
X-API-Key: <your-api-key>
```

**Request body:**
```json
{
  "recipient":   "user@example.com",
  "subject":     "Account Verification",
  "sender_name": "Mensor Service",
  "html_body":   "<h1>Hello!</h1><p>Click <a href='https://example.com'>here</a>.</p>"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `recipient` | string | ✅ | Recipient email address |
| `subject` | string | ✅ | Email subject line |
| `sender_name` | string | ✅ | Display name of the sender |
| `html_body` | string | ✅ | Full HTML content of the email |

**Success response (`200`):**
```json
{
  "ok": true
}
```

**Error responses:**

| HTTP | Meaning |
|------|---------|
| `400` | Validation error (missing/invalid fields) |
| `401` | Invalid or missing API key |
| `502` | SMTP server error |

**Example (curl):**
```bash
curl -X POST http://your-server:8080/api/v1/mail/send \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "recipient": "user@example.com",
    "subject": "Welcome!",
    "sender_name": "Mensor",
    "html_body": "<h1>Welcome to our service!</h1>"
  }'
```

**Example (Python):**
```python
import httpx

response = httpx.post(
    "http://your-server:8080/api/v1/mail/send",
    headers={"X-API-Key": "your-api-key-here"},
    json={
        "recipient": "user@example.com",
        "subject": "Welcome!",
        "sender_name": "Mensor",
        "html_body": "<h1>Welcome to our service!</h1>",
    },
)
data = response.json()
print("OK" if data["ok"] else "Error: " + data["error"])
```

---

### `POST /api/v1/screen/generate`

Generate a fake bank-screenshot PNG image.

**Headers:**
```
Content-Type: application/json
X-API-Key: <your-api-key>
```

**Request body:**
```json
{
  "country":      "ch",
  "platform":     "bank",
  "service_name": "Netflix",
  "amount":       12.99
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `country` | string | ✅ | `"ch"` (Switzerland, CHF) or `"de"` (Germany, EUR) |
| `platform` | string | ✅ | `"bank"` (simple screenshot) or `"full_tranz"` (detailed transaction view) |
| `service_name` | string | ✅ | Name of the service shown on the screenshot. Maximum **40 characters** |
| `amount` | number | ✅ | Debit amount (positive number, e.g. `12.99`) |

**Success response (`200`):**

The response body is the raw **PNG image** bytes.

```
Content-Type: image/png
```

Save it directly to a file or forward it as a photo in Telegram.

**Error responses:**

| HTTP | Meaning |
|------|---------|
| `400` | Validation error (missing/invalid fields) |
| `401` | Invalid or missing API key |
| `500` | Image generation failed |

**Example (curl):**
```bash
curl -X POST http://your-server:8080/api/v1/screen/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "country": "ch",
    "platform": "bank",
    "service_name": "Spotify",
    "amount": 9.99
  }' \
  --output screen.png
```

**Example (Python + aiogram — send PNG to Telegram):**
```python
import httpx
from aiogram.types import BufferedInputFile

async def send_screen(bot, chat_id: int, api_key: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://your-server:8080/api/v1/screen/generate",
            headers={"X-API-Key": api_key},
            json={
                "country": "ch",
                "platform": "bank",
                "service_name": "Netflix",
                "amount": 14.99,
            },
        )
    if response.status_code == 200:
        await bot.send_photo(
            chat_id=chat_id,
            photo=BufferedInputFile(response.content, filename="screen.png"),
            caption="✅ Скриншот готов",
        )
    else:
        error = response.json().get("error", "unknown")
        await bot.send_message(chat_id, f"❌ Ошибка: {error}")
```

---

## Error Format

All error responses follow this format:

```json
{
  "ok": false,
  "error": "Human-readable error message"
}
```

---

## Admin: API Key Management

API keys are managed exclusively by the bot administrator:

1. Open the bot and send `/admin`
2. Press **🔑 API ключи партнёров**
3. Use **➕ Создать API ключ** to create a new key — enter the partner name when prompted
4. The generated key is shown **once** — copy and share it with your partner
5. Use **📋 Список API ключей** to view all keys (active/revoked)
6. A key can be **revoked** (temporarily disabled) or **deleted** (permanently removed)

---

## Security Notes

- API keys are **40-character random hex strings** (`secrets.token_hex(20)`)
- Keys are stored in the database; they are **not recoverable** after creation — save them immediately
- Revoking a key immediately blocks all requests using that key
- Deploy the API server behind a reverse proxy (nginx, Caddy) with HTTPS for production use
- Set `API_HOST=127.0.0.1` in `.env` if the API is only accessed via localhost/proxy

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Interface to bind (use `127.0.0.1` behind a proxy) |
| `API_PORT` | `8080` | TCP port for the API server |

These are set in the `.env` file alongside the other bot configuration.

---

## Rate Limits

**There are no rate limits for API users.** Partner bots using a valid API key can call all endpoints without restrictions (no daily email limit, no SMS quota).

---

## Quick Integration Example (partner bot)

```python
# partner_bot/api.py
import httpx

MENSOR_API_URL = "http://mensor-server:8080"
MENSOR_API_KEY = "your-api-key-here"

_headers = {"X-API-Key": MENSOR_API_KEY, "Content-Type": "application/json"}


async def send_sms(phone: str, text: str, sender: str = "") -> bool:
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{MENSOR_API_URL}/api/v1/sms/send", headers=_headers,
                         json={"phone": phone, "text": text, "sender": sender})
    return r.json().get("ok", False)


async def send_email(recipient: str, subject: str, sender_name: str, html: str) -> bool:
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{MENSOR_API_URL}/api/v1/mail/send", headers=_headers,
                         json={"recipient": recipient, "subject": subject,
                               "sender_name": sender_name, "html_body": html})
    return r.json().get("ok", False)


async def generate_screen(country: str, platform: str, service: str, amount: float) -> bytes | None:
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{MENSOR_API_URL}/api/v1/screen/generate", headers=_headers,
                         json={"country": country, "platform": platform,
                               "service_name": service, "amount": amount})
    if r.status_code == 200:
        return r.content
    return None
```


---

### `POST /api/v1/pdf/generate`

Generate a Switzerland promo PDF document (Ricardo or PostFinance/Post), in German or French.

**Headers:**
```
Content-Type: application/json
X-API-Key: <your-api-key>
```

**Request body:**
```json
{
  "template":      "ricardo",
  "lang":          "de",
  "buyer_name":    "Max Mustermann",
  "delivery":      "A-Post",
  "product_name":  "iPhone 15 Pro",
  "amount":        "1299.00",
  "link":          "https://pay.example.com/invoice/abc123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `template` | string | ✅ | `"ricardo"` or `"post"` |
| `lang` | string | ✅ | `"de"` (German) or `"fr"` (French) |
| `buyer_name` | string | ✅ | Full name of the buyer (NUMBER2 placeholder). Maximum **80 characters** |
| `delivery` | string | ✅ | Delivery or payment method (NUMBER3 placeholder) |
| `product_name` | string | ✅ | Product name shown on the document (NUMBER4 placeholder). Maximum **80 characters** |
| `amount` | string | ✅ | Amount in CHF as a string (NUMBER5 placeholder), e.g. `"49.90"` |
| `link` | string | ✅ | Payment link inserted as FISHLINK placeholder |

**Success response (`200`):**

The response body is the raw **PDF** bytes.

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="Ricardo_123456_01.04.2026.pdf"
```

Save it directly to a file or forward it as a document in Telegram.

**Error responses:**

| HTTP | Meaning |
|------|---------|
| `400` | Validation error (missing/invalid fields) |
| `401` | Invalid or missing API key |
| `500` | PDF generation failed |

**Template placeholder mapping:**

| Placeholder | Field | Description |
|-------------|-------|-------------|
| `NUMBER2` | `buyer_name` | Buyer's full name |
| `NUMBER3` | `delivery` | Delivery or payment method |
| `NUMBER4` | `product_name` | Product name |
| `NUMBER5` | `amount` | Amount in CHF |
| `FISHLINK` | `link` | Payment link |
| `DATA` | *(auto)* | Current date in `dd.mm.yyyy` format |

**Filename format:** `{Platform}_{6-digit-random}_{dd.mm.yyyy}.pdf`  
Examples: `Ricardo_847291_01.04.2026.pdf`, `POST_019384_01.04.2026.pdf`

**Example (curl):**
```bash
curl -X POST http://your-server:8080/api/v1/pdf/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "template": "ricardo",
    "lang": "de",
    "buyer_name": "Anna Müller",
    "delivery": "A-Post",
    "product_name": "MacBook Pro 14",
    "amount": "2799.00",
    "link": "https://pay.example.com/invoice/xyz"
  }' \
  --output invoice.pdf
```

**Example (Python + aiogram — send PDF to Telegram):**
```python
import httpx
from aiogram.types import BufferedInputFile

async def send_promo_pdf(bot, chat_id: int, api_key: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://your-server:8080/api/v1/pdf/generate",
            headers={"X-API-Key": api_key},
            json={
                "template": "post",
                "lang": "fr",
                "buyer_name": "Jean Dupont",
                "delivery": "Envoi prioritaire",
                "product_name": "Samsung Galaxy S24",
                "amount": "899.00",
                "link": "https://pay.example.com/fr/invoice/abc",
            },
        )
    if response.status_code == 200:
        filename = "POST_invoice.pdf"
        cd = response.headers.get("Content-Disposition", "")
        if 'filename="' in cd:
            filename = cd.split('filename="')[1].rstrip('"')
        await bot.send_document(
            chat_id=chat_id,
            document=BufferedInputFile(response.content, filename=filename),
            caption="✅ PDF готов",
        )
    else:
        error = response.json().get("error", "unknown")
        await bot.send_message(chat_id, f"❌ Ошибка: {error}")
```

---
