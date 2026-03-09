"""Tests for phone normalization utilities."""

from app.utils.phone_utils import normalize_phone_for_comparison, normalize_phone_for_storage


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


class TestNormalizePhoneForStorage:
    """Tests for normalize_phone_for_storage."""

    def test_us_ten_digit_number_gets_default_country_code(self) -> None:
        assert normalize_phone_for_storage("3125219788") == "+13125219788"

    def test_formatted_us_number_gets_default_country_code(self) -> None:
        assert normalize_phone_for_storage("(312) 521-9788") == "+13125219788"

    def test_existing_e164_is_preserved(self) -> None:
        assert normalize_phone_for_storage("+1 (312) 521-9788") == "+13125219788"

    def test_empty_returns_none(self) -> None:
        assert normalize_phone_for_storage("") is None
        assert normalize_phone_for_storage("   ") is None
        assert normalize_phone_for_storage(None) is None
