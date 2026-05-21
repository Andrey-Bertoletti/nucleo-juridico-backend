"""Validadores reutilizáveis para documentos e contatos brasileiros."""

import re
from datetime import date


_DIGITS_ONLY = re.compile(r"\D")


def only_digits(value: str | None) -> str:
    if value is None:
        return ""
    return _DIGITS_ONLY.sub("", value)


# ---------------------------------------------------------------------------
# CPF
# ---------------------------------------------------------------------------
def is_valid_cpf(value: str | None) -> bool:
    """Valida CPF brasileiro (11 dígitos + dígitos verificadores)."""
    cpf = only_digits(value)
    if len(cpf) != 11:
        return False
    # Rejeita CPFs com todos os dígitos iguais (000..., 111..., etc.).
    if cpf == cpf[0] * 11:
        return False

    # Primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito_1 = (soma * 10) % 11
    if digito_1 == 10:
        digito_1 = 0
    if digito_1 != int(cpf[9]):
        return False

    # Segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito_2 = (soma * 10) % 11
    if digito_2 == 10:
        digito_2 = 0
    if digito_2 != int(cpf[10]):
        return False

    return True


# ---------------------------------------------------------------------------
# RG — formato (não há algoritmo nacional; varia por estado)
# ---------------------------------------------------------------------------
_RG_CHARS = re.compile(r"[^0-9Xx]")


def is_valid_rg(value: str | None) -> bool:
    if value is None or value == "":
        return True  # RG é opcional
    cleaned = _RG_CHARS.sub("", value)
    if not (5 <= len(cleaned) <= 14):
        return False
    if cleaned == cleaned[0] * len(cleaned):  # tudo igual
        return False
    return True


def normalize_rg(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = _RG_CHARS.sub("", value)
    return cleaned.upper() or None


# ---------------------------------------------------------------------------
# Telefone (BR: 10 ou 11 dígitos com DDD)
# ---------------------------------------------------------------------------
def is_valid_phone(value: str | None) -> bool:
    if value is None or value == "":
        return True  # opcional
    digits = only_digits(value)
    if len(digits) not in (10, 11):
        return False
    # DDD válido começa com 1-9
    if digits[0] == "0":
        return False
    return True


# ---------------------------------------------------------------------------
# Data de nascimento
# ---------------------------------------------------------------------------
MIN_BIRTH_YEAR = 1900


def is_valid_birth_date(value: date | None) -> bool:
    if value is None:
        return True  # opcional
    today = date.today()
    if value > today:
        return False
    if value.year < MIN_BIRTH_YEAR:
        return False
    return True
