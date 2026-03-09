"""Tests for merchant favicon_url in services."""

import pytest

from app.merchants import services as merchant_services
from app.merchants.models import Merchant


def test_create_merchant_with_favicon_url(app, test_user) -> None:
    """create_merchant accepts favicon_url and persists it."""
    with app.app_context():
        merchant = merchant_services.create_merchant(
            test_user.id,
            {
                "name": "Brand With Icon",
                "favicon_url": "https://example.com/favicon.ico",
            },
        )
        assert merchant.favicon_url == "https://example.com/favicon.ico"


def test_create_merchant_invalid_favicon_url_ignored(app, test_user) -> None:
    """Invalid favicon_url is not stored."""
    with app.app_context():
        merchant = merchant_services.create_merchant(
            test_user.id,
            {
                "name": "Brand No Icon",
                "favicon_url": "ftp://example.com/icon.ico",
            },
        )
        assert merchant.favicon_url is None


def test_update_merchant_favicon_url(app, test_user) -> None:
    """update_merchant can set and clear favicon_url."""
    with app.app_context():
        merchant = merchant_services.create_merchant(
            test_user.id,
            {"name": "Update Favicon Test"},
        )
        assert merchant.favicon_url is None

        merchant_services.update_merchant(
            merchant.id,
            {"favicon_url": "https://brand.com/icon.png"},
        )
        updated = merchant_services.get_merchant(merchant.id)
        assert updated is not None
        assert updated.favicon_url == "https://brand.com/icon.png"

        merchant_services.update_merchant(merchant.id, {"favicon_url": ""})
        cleared = merchant_services.get_merchant(merchant.id)
        assert cleared is not None
        assert cleared.favicon_url is None
