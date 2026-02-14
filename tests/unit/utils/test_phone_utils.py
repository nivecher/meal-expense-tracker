"""Tests for phone normalization utilities."""

import pytest

from app.utils.phone_utils import normalize_phone_for_comparison


class TestNormalizePhoneForComparison:
    """Tests for normalize_phone_for_comparison."""

    def test_digits_only(self) -> None:
        assert normalize_phone_for_comparison("5551234567") == "5551234567"

    def test_formatted_us_phone(self) -> None:
        assert normalize_phone_for_comparison("(555) 123-4567") == "5551234567"

    def test_dashes(self) -> None:
        assert normalize_phone_for_comparison("555-123-4567") == "5551234567"

    def test_with_country_code(self) -> None:
        assert normalize_phone_for_comparison("+1 555-123-4567") == "15551234567"

    def test_dots(self) -> None:
        assert normalize_phone_for_comparison("555.123.4567") == "5551234567"

    def test_empty_returns_empty(self) -> None:
        assert normalize_phone_for_comparison("") == ""
        assert normalize_phone_for_comparison("   ") == ""
        assert normalize_phone_for_comparison(None) == ""
