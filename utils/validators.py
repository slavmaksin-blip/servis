import re


def validate_phone_number(phone: str, expected_digits: int) -> tuple[bool, str]:
    digits = re.sub(r"\D", "", phone)
    if len(digits) != expected_digits:
        return False, f"Номер должен содержать {expected_digits} цифр (без кода страны)."
    return True, ""


def validate_sender_name(name: str) -> tuple[bool, str]:
    if not name:
        return False, "Имя отправителя не может быть пустым."
    if len(name) > 12:
        return False, "Имя отправителя не может быть длиннее 12 символов."
    if not re.match(r"^[A-Za-z0-9 \-_.]+$", name):
        return False, "Имя отправителя может содержать только латинские буквы, цифры и символы: - _ ."
    return True, ""


def validate_sms_content(text: str) -> tuple[bool, str]:
    if not text:
        return False, "Текст SMS не может быть пустым."
    if len(text) > 160:
        return False, f"Текст SMS слишком длинный ({len(text)}/160 символов)."
    return True, ""


def validate_amount(value: str) -> tuple[bool, str]:
    try:
        amount = float(value)
    except ValueError:
        return False, "Введите числовое значение."
    if amount < 1:
        return False, "Минимальная сумма — $1.00."
    return True, ""


def validate_promo_code(code: str) -> tuple[bool, str]:
    if not code:
        return False, "Промокод не может быть пустым."
    if len(code) < 3 or len(code) > 32:
        return False, "Длина промокода должна быть от 3 до 32 символов."
    if not re.match(r"^[A-Za-z0-9_\-]+$", code):
        return False, "Промокод может содержать только латинские буквы, цифры, - и _."
    return True, ""
