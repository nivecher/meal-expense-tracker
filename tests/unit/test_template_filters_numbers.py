"""Tests for number formatting template filters."""

import pytest


@pytest.mark.usefixtures("app")
class TestNumberFormattingFilters:
    def test_format_number_adds_commas(self, app) -> None:
        assert app.jinja_env.filters["format_number"](1234, 0) == "1,234"
        assert app.jinja_env.filters["format_number"](1234.5, 2) == "1,234.50"

    def test_format_number_handles_none(self, app) -> None:
        assert app.jinja_env.filters["format_number"](None) == ""

    def test_format_currency_usd(self, app) -> None:
        assert app.jinja_env.filters["format_currency_usd"](0) == "$0.00"
        assert app.jinja_env.filters["format_currency_usd"](1234.5) == "$1,234.50"
        assert app.jinja_env.filters["format_currency_usd"](-12.3) == "-$12.30"
