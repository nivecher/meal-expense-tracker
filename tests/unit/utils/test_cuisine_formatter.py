"""
Tests for cuisine formatter utilities.

This module tests the cuisine formatting functions that handle Google Places data
and provide consistent formatting across the application.
"""

from unittest.mock import patch

from app.utils.cuisine_formatter import (
    _capitalize_words,
    format_cuisine_type,
    get_available_cuisine_types,
    get_cuisine_display_name,
    validate_cuisine_type,
)


class TestFormatCuisineType:
    """Test format_cuisine_type function."""

    @patch("app.utils.cuisine_formatter.get_cuisine_data")
    def test_format_cuisine_type_with_known_cuisine(self, mock_get_cuisine_data):
        """Test formatting with known cuisine type."""
        mock_get_cuisine_data.return_value = {"name": "Mexican"}

        result = format_cuisine_type("mexican")
        assert result == "Mexican"
        mock_get_cuisine_data.assert_called_once_with("mexican")

    @patch("app.utils.cuisine_formatter.get_cuisine_data")
    def test_format_cuisine_type_with_unknown_cuisine(self, mock_get_cuisine_data):
        """Test formatting with unknown cuisine type."""
        mock_get_cuisine_data.return_value = None

        result = format_cuisine_type("mexican")
        assert result == "Mexican"  # Should capitalize the word

    @patch("app.utils.cuisine_formatter.get_cuisine_data")
    def test_format_cuisine_type_with_underscores(self, mock_get_cuisine_data):
        """Test formatting with underscores in cuisine type."""
        mock_get_cuisine_data.return_value = None

        result = format_cuisine_type("mexican_restaurant")
        assert result == "Mexican Restaurant"

    @patch("app.utils.cuisine_formatter.get_cuisine_data")
    def test_format_cuisine_type_with_dashes(self, mock_get_cuisine_data):
        """Test formatting with dashes in cuisine type."""
        mock_get_cuisine_data.return_value = None

        result = format_cuisine_type("fast-food")
        assert result == "Fast Food"

    @patch("app.utils.cuisine_formatter.get_cuisine_data")
    def test_format_cuisine_type_mixed_separators(self, mock_get_cuisine_data):
        """Test formatting with mixed separators."""
        mock_get_cuisine_data.return_value = None

        result = format_cuisine_type("mexican_fast-food")
        assert result == "Mexican Fast Food"

    def test_format_cuisine_type_none_input(self):
        """Test formatting with None input."""
        result = format_cuisine_type(None)
        assert result == ""

    def test_format_cuisine_type_empty_string(self):
        """Test formatting with empty string."""
        result = format_cuisine_type("")
        assert result == ""

    def test_format_cuisine_type_whitespace_only(self):
        """Test formatting with whitespace-only string."""
        result = format_cuisine_type("   ")
        assert result == ""

    def test_format_cuisine_type_non_string(self):
        """Test formatting with non-string input."""
        result = format_cuisine_type(123)
        assert result == ""

    def test_format_cuisine_type_too_long(self):
        """Test formatting with string exceeding max length."""
        long_string = "a" * 101
        result = format_cuisine_type(long_string, max_length=100)
        assert result == ""

    def test_format_cuisine_type_exact_max_length(self):
        """Test formatting with string at exact max length."""
        long_string = "a" * 100
        result = format_cuisine_type(long_string, max_length=100)
        assert result == "A" + "a" * 99  # Only first letter is capitalized

    def test_format_cuisine_type_custom_max_length(self):
        """Test formatting with custom max length."""
        result = format_cuisine_type("mexican", max_length=50)
        assert result == "Mexican"

    def test_format_cuisine_type_uppercase_input(self):
        """Test formatting with uppercase input."""
        result = format_cuisine_type("ITALIAN")
        assert result == "Italian"

    def test_format_cuisine_type_mixed_case(self):
        """Test formatting with mixed case input."""
        result = format_cuisine_type("mExIcAn")
        assert result == "Mexican"


class TestCapitalizeWords:
    """Test _capitalize_words function."""

    def test_capitalize_words_simple(self):
        """Test simple word capitalization."""
        result = _capitalize_words("mexican")
        assert result == "Mexican"

    def test_capitalize_words_multiple_words(self):
        """Test multiple words capitalization."""
        result = _capitalize_words("mexican restaurant")
        assert result == "Mexican Restaurant"

    def test_capitalize_words_with_underscores(self):
        """Test capitalization with underscores."""
        result = _capitalize_words("mexican_restaurant")
        assert result == "Mexican Restaurant"

    def test_capitalize_words_with_dashes(self):
        """Test capitalization with dashes."""
        result = _capitalize_words("fast-food")
        assert result == "Fast Food"

    def test_capitalize_words_mixed_separators(self):
        """Test capitalization with mixed separators."""
        result = _capitalize_words("mexican_fast-food")
        assert result == "Mexican Fast Food"

    def test_capitalize_words_empty_string(self):
        """Test capitalization with empty string."""
        result = _capitalize_words("")
        assert result == ""

    def test_capitalize_words_none_input(self):
        """Test capitalization with None input."""
        result = _capitalize_words(None)
        assert result == ""

    def test_capitalize_words_whitespace_only(self):
        """Test capitalization with whitespace-only string."""
        result = _capitalize_words("   ")
        assert result == ""

    def test_capitalize_words_just_separators(self):
        """Test capitalization with just separators."""
        result = _capitalize_words("___---")
        assert result == ""

    def test_capitalize_words_single_character(self):
        """Test capitalization with single character."""
        result = _capitalize_words("a")
        assert result == "A"

    def test_capitalize_words_numbers(self):
        """Test capitalization with numbers."""
        result = _capitalize_words("restaurant123")
        assert result == "Restaurant123"

    def test_capitalize_words_already_capitalized(self):
        """Test capitalization with already capitalized words."""
        result = _capitalize_words("Mexican Restaurant")
        assert result == "Mexican Restaurant"

    def test_capitalize_words_special_characters(self):
        """Test capitalization with special characters."""
        result = _capitalize_words("mexican's restaurant")
        assert result == "Mexican's Restaurant"


class TestGetCuisineDisplayName:
    """Test get_cuisine_display_name function."""

    @patch("app.utils.cuisine_formatter.format_cuisine_type")
    def test_get_cuisine_display_name_valid(self, mock_format):
        """Test display name with valid cuisine type."""
        mock_format.return_value = "Mexican"

        result = get_cuisine_display_name("mexican")
        assert result == "Mexican"
        mock_format.assert_called_once_with("mexican")

    @patch("app.utils.cuisine_formatter.format_cuisine_type")
    def test_get_cuisine_display_name_empty_result(self, mock_format):
        """Test display name with empty formatting result."""
        mock_format.return_value = ""

        result = get_cuisine_display_name("invalid")
        assert result == "Unknown"

    def test_get_cuisine_display_name_none_input(self):
        """Test display name with None input."""
        result = get_cuisine_display_name(None)
        assert result == "Unknown"

    def test_get_cuisine_display_name_empty_string(self):
        """Test display name with empty string."""
        result = get_cuisine_display_name("")
        assert result == "Unknown"

    @patch("app.utils.cuisine_formatter.format_cuisine_type")
    def test_get_cuisine_display_name_whitespace_result(self, mock_format):
        """Test display name with whitespace-only formatting result."""
        mock_format.return_value = "   "

        result = get_cuisine_display_name("whitespace")
        assert result == "   "  # The function returns the formatted result as-is


class TestValidateCuisineType:
    """Test validate_cuisine_type function."""

    @patch("app.utils.cuisine_formatter.get_cuisine_data")
    def test_validate_cuisine_type_known_cuisine(self, mock_get_cuisine_data):
        """Test validation with known cuisine type."""
        mock_get_cuisine_data.return_value = {"name": "Mexican"}

        result = validate_cuisine_type("mexican")
        assert result is True
        mock_get_cuisine_data.assert_called_once_with("mexican")

    @patch("app.utils.cuisine_formatter.get_cuisine_data")
    @patch("app.utils.cuisine_formatter.format_cuisine_type")
    def test_validate_cuisine_type_unknown_but_formattable(self, mock_format, mock_get_cuisine_data):
        """Test validation with unknown but formattable cuisine type."""
        mock_get_cuisine_data.return_value = None
        mock_format.return_value = "Mexican"

        result = validate_cuisine_type("mexican")
        assert result is True

    @patch("app.utils.cuisine_formatter.get_cuisine_data")
    @patch("app.utils.cuisine_formatter.format_cuisine_type")
    def test_validate_cuisine_type_unknown_and_unformattable(self, mock_format, mock_get_cuisine_data):
        """Test validation with unknown and unformattable cuisine type."""
        mock_get_cuisine_data.return_value = None
        mock_format.return_value = ""

        result = validate_cuisine_type("xyz123")
        assert result is False

    @patch("app.utils.cuisine_formatter.get_cuisine_data")
    @patch("app.utils.cuisine_formatter.format_cuisine_type")
    def test_validate_cuisine_type_whitespace_formatted(self, mock_format, mock_get_cuisine_data):
        """Test validation with whitespace-only formatted result."""
        mock_get_cuisine_data.return_value = None
        mock_format.return_value = "   "

        result = validate_cuisine_type("whitespace")
        assert result is False

    def test_validate_cuisine_type_none_input(self):
        """Test validation with None input."""
        result = validate_cuisine_type(None)
        assert result is False

    def test_validate_cuisine_type_empty_string(self):
        """Test validation with empty string."""
        result = validate_cuisine_type("")
        assert result is False


class TestGetAvailableCuisineTypes:
    """Test get_available_cuisine_types function."""

    @patch("app.utils.cuisine_formatter.get_cuisine_names")
    def test_get_available_cuisine_types(self, mock_get_cuisine_names):
        """Test getting available cuisine types."""
        mock_cuisines = ["Chinese", "Italian", "Japanese", "Mexican"]
        mock_get_cuisine_names.return_value = mock_cuisines

        result = get_available_cuisine_types()
        assert result == mock_cuisines
        mock_get_cuisine_names.assert_called_once()

    @patch("app.utils.cuisine_formatter.get_cuisine_names")
    def test_get_available_cuisine_types_empty(self, mock_get_cuisine_names):
        """Test getting available cuisine types when none available."""
        mock_get_cuisine_names.return_value = []

        result = get_available_cuisine_types()
        assert result == []


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @patch("app.utils.cuisine_formatter.get_cuisine_data")
    def test_format_cuisine_type_very_long_input(self, mock_get_cuisine_data):
        """Test formatting with very long input."""
        mock_get_cuisine_data.return_value = None

        # Test with input just under max length
        long_input = "a" * 99
        result = format_cuisine_type(long_input, max_length=100)
        assert result == "A" + "a" * 98  # Only first letter is capitalized

    def test_capitalize_words_complex_separators(self):
        """Test capitalization with complex separator patterns."""
        result = _capitalize_words("mexican_fast-food_restaurant")
        assert result == "Mexican Fast Food Restaurant"

    def test_capitalize_words_multiple_spaces(self):
        """Test capitalization with multiple spaces."""
        result = _capitalize_words("mexican    restaurant")
        assert result == "Mexican Restaurant"

    @patch("app.utils.cuisine_formatter.get_cuisine_data")
    def test_format_cuisine_type_unicode(self, mock_get_cuisine_data):
        """Test formatting with unicode characters."""
        mock_get_cuisine_data.return_value = None

        result = format_cuisine_type("café")
        assert result == "Café"

    def test_capitalize_words_unicode(self):
        """Test capitalization with unicode characters."""
        result = _capitalize_words("café_restaurant")
        assert result == "Café Restaurant"

    @patch("app.utils.cuisine_formatter.get_cuisine_data")
    def test_format_cuisine_type_special_characters(self, mock_get_cuisine_data):
        """Test formatting with special characters."""
        mock_get_cuisine_data.return_value = None

        result = format_cuisine_type("mexican's_restaurant")
        assert result == "Mexican's Restaurant"

    def test_capitalize_words_empty_after_split(self):
        """Test capitalization with empty words after splitting."""
        result = _capitalize_words("___")
        assert result == ""

    def test_capitalize_words_single_underscore(self):
        """Test capitalization with single underscore."""
        result = _capitalize_words("_")
        assert result == ""

    def test_capitalize_words_single_dash(self):
        """Test capitalization with single dash."""
        result = _capitalize_words("-")
        assert result == ""
