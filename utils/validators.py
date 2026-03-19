import re


def validate_phone(phone: str) -> bool:
    """Validate international phone number format."""
    pattern = r"^\+?[1-9]\d{7,14}$"
    return bool(re.match(pattern, phone.strip()))


def validate_amount(amount_str: str) -> float | None:
    """Parse and validate a monetary amount. Returns None if invalid or zero."""
    try:
        value = float(amount_str.replace(",", ".").strip())
        if value != 0:
            return round(value, 2)
    except ValueError:
        pass
    return None


def sanitize_message(text: str, max_length: int = 160) -> str:
    """Strip leading/trailing whitespace and truncate to SMS length."""
    return text.strip()[:max_length]
