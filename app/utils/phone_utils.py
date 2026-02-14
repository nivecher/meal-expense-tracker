"""Phone number normalization utilities for comparison."""

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
