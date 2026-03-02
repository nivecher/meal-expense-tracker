"""Tests for URL normalization utilities."""

import pytest

from app.utils.url_utils import normalize_website_for_comparison, strip_url_query_params


class TestStripUrlQueryParams:
    """Tests for strip_url_query_params."""

    def test_strips_utm_params(self) -> None:
        url = "https://example.com/?utm_source=google&utm_medium=organic"
        assert strip_url_query_params(url) == "https://example.com/"

    def test_no_params_unchanged(self) -> None:
        url = "https://example.com/"
        assert strip_url_query_params(url) == url

    def test_preserves_fragment(self) -> None:
        url = "https://example.com/page#section"
        assert strip_url_query_params(url) == url


class TestNormalizeWebsiteForComparison:
    """Tests for normalize_website_for_comparison."""

    def test_strips_params_and_trailing_slash(self) -> None:
        a = normalize_website_for_comparison("https://example.com/?utm=1")
        b = normalize_website_for_comparison("https://example.com/")
        assert a == b

    def test_lowercase(self) -> None:
        assert normalize_website_for_comparison("HTTPS://Example.COM/") == "https://example.com/"

    def test_empty_returns_empty(self) -> None:
        assert normalize_website_for_comparison("") == ""
        assert normalize_website_for_comparison(None) == ""
