"""
Validators for user input.
"""

import re

# Phone number pattern: +41 followed by exactly 9 digits
# Format: +41xxxxxxxxx  (e.g. +41791234567)
_PHONE_PATTERN = re.compile(r"^\+41\d{9}$")


def validate_phone_number(phone: str) -> bool:
    """
    Validate a Swiss-format phone number.

    Expected format: +41 followed by exactly 9 digits.
    Examples of valid numbers:
        +41791234567
        +41441234567

    Parameters
    ----------
    phone : str
        Phone number string to validate.

    Returns
    -------
    bool
        True if the phone number is valid, False otherwise.
    """
    if not isinstance(phone, str):
        return False
    return bool(_PHONE_PATTERN.match(phone.strip()))


PHONE_FORMAT_ERROR_MESSAGE = (
    "❌ Неверный формат номера телефона.\n"
    "Введите номер в формате: <b>+41XXXXXXXXX</b>\n"
    "• +41 — код страны (Швейцария)\n"
    "• XXXXXXXXX — ровно 9 цифр\n"
    "Пример: +41791234567"
)
