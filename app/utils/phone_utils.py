"""Phone number normalization utilities."""

import re


def normalize_phone_for_comparison(phone: str | None) -> str:
    """Normalize phone number to digits-only for comparison.

    Strips spaces, dashes, parentheses, dots, and plus/country code for
    semantic comparison. E.g. "(555) 123-4567" and "555-123-4567" both
    normalize to "5551234567".

    Args:
        phone: Raw phone number string

    Returns:
        Digits-only string, or empty string if input is empty/invalid
    """
    if not phone or not isinstance(phone, str):
        return ""
    digits = re.sub(r"\D", "", phone.strip())
    return digits


def normalize_phone_for_storage(phone: str | None, default_country_code: str = "1") -> str | None:
    """Normalize phone input for storage.

    Rules:
    - Empty input becomes ``None``.
    - Numbers already written with ``+`` are reduced to ``+`` plus digits.
    - Plain 10-digit US numbers become ``+1XXXXXXXXXX``.
    - Plain 11-digit US numbers starting with ``1`` become ``+1XXXXXXXXXX``.
    - Other inputs are returned trimmed so non-US/incomplete values are not destroyed.
    """
    if phone is None or not isinstance(phone, str):
        return None

    raw = phone.strip()
    if not raw:
        return None

    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None

    if raw.startswith("+"):
        return f"+{digits}"

    if len(digits) == 10:
        return f"+{default_country_code}{digits}"

    if len(digits) == 11 and digits.startswith(default_country_code):
        return f"+{digits}"

    return raw
