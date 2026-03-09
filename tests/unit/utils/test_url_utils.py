"""Tests for URL normalization utilities."""

import pytest

from app.utils.url_utils import (
    canonicalize_website_for_storage,
    get_favicon_host_candidates,
    normalize_website_for_comparison,
    strip_url_query_params,
    validate_favicon_url,
)


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


class TestCanonicalizeWebsiteForStorage:
    """Tests for canonicalize_website_for_storage."""

    def test_strips_query_and_fragment(self) -> None:
        assert canonicalize_website_for_storage("https://example.com/path?x=1#a") == "https://example.com/path"

    def test_lowercase_host(self) -> None:
        assert canonicalize_website_for_storage("https://Example.COM/") == "https://example.com/"

    def test_defaults_to_https_when_no_scheme(self) -> None:
        # URL with no scheme but with netloc (e.g. //example.com/) gets https
        assert canonicalize_website_for_storage("//example.com/") == "https://example.com/"
        assert canonicalize_website_for_storage("http://example.com/") == "http://example.com/"

    def test_empty_or_invalid_returns_none(self) -> None:
        assert canonicalize_website_for_storage("") is None
        assert canonicalize_website_for_storage(None) is None

    def test_chick_fil_a_www_preserved(self) -> None:
        """Regression: www and apex both canonicalize to consistent form."""
        a = canonicalize_website_for_storage("https://www.chick-fil-a.com/")
        b = canonicalize_website_for_storage("https://chick-fil-a.com/")
        assert a == "https://www.chick-fil-a.com/"
        assert b == "https://chick-fil-a.com/"


class TestGetFaviconHostCandidates:
    """Tests for get_favicon_host_candidates (www/apex fallback for favicon resolution)."""

    def test_returns_primary_and_alternate(self) -> None:
        # www first -> apex as alternate
        assert get_favicon_host_candidates("https://www.chick-fil-a.com/") == [
            "www.chick-fil-a.com",
            "chick-fil-a.com",
        ]
        # apex first -> www as alternate
        assert get_favicon_host_candidates("https://chick-fil-a.com/") == [
            "chick-fil-a.com",
            "www.chick-fil-a.com",
        ]

    def test_chick_fil_a_regression(self) -> None:
        """Regression: Chick-fil-A favicon works for both apex and www (candidates try both)."""
        from_www = get_favicon_host_candidates("https://www.chick-fil-a.com/")
        from_apex = get_favicon_host_candidates("https://chick-fil-a.com/")
        assert "www.chick-fil-a.com" in from_www
        assert "chick-fil-a.com" in from_www
        assert "www.chick-fil-a.com" in from_apex
        assert "chick-fil-a.com" in from_apex

    def test_empty_or_invalid_returns_empty_list(self) -> None:
        assert get_favicon_host_candidates("") == []
        assert get_favicon_host_candidates(None) == []

    def test_single_host_no_www(self) -> None:
        assert get_favicon_host_candidates("https://example.com/") == [
            "example.com",
            "www.example.com",
        ]


class TestValidateFaviconUrl:
    """Tests for validate_favicon_url (merchant favicon override)."""

    def test_valid_https_returns_url(self) -> None:
        url = "https://example.com/favicon.ico"
        assert validate_favicon_url(url) == url

    def test_valid_http_returns_url(self) -> None:
        url = "http://example.com/icon.png"
        assert validate_favicon_url(url) == url

    def test_empty_returns_none(self) -> None:
        assert validate_favicon_url("") is None
        assert validate_favicon_url(None) is None
        assert validate_favicon_url("   ") is None

    def test_invalid_scheme_returns_none(self) -> None:
        assert validate_favicon_url("ftp://example.com/favicon.ico") is None
        assert validate_favicon_url("javascript:alert(1)") is None

    def test_no_netloc_returns_none(self) -> None:
        assert validate_favicon_url("https://") is None
