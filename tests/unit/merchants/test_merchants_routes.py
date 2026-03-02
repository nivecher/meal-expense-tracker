"""Tests for merchant routes."""

from flask import url_for

from app.auth.models import User
from app.extensions import db
from app.merchants.models import Merchant


def _enable_advanced_features(user: User) -> None:
    user.advanced_features_enabled = True
    db.session.add(user)
    db.session.commit()


def _create_merchant(name: str = "Acme Coffee") -> Merchant:
    merchant = Merchant(name=name, short_name="Acme", category="coffee_shop", website="https://acme.example")
    db.session.add(merchant)
    db.session.commit()
    return merchant


def test_export_merchants_csv(client, auth, test_user) -> None:
    """Export merchants in CSV format."""
    _enable_advanced_features(test_user)
    _create_merchant()
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("merchants.export_merchants"))

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")
    assert "merchants.csv" in response.headers.get("Content-Disposition", "")


def test_export_merchants_json(client, auth, test_user) -> None:
    """Export merchants in JSON format."""
    _enable_advanced_features(test_user)
    _create_merchant("Sunset Grill Group")
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("merchants.export_merchants"), query_string={"format": "json"})

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert "merchants.json" in response.headers.get("Content-Disposition", "")
    payload = response.get_json()
    assert isinstance(payload, list)
    assert any(item.get("name") == "Sunset Grill Group" for item in payload)


def test_export_merchants_selected_ids(client, auth, test_user) -> None:
    """Export only selected merchant IDs."""
    _enable_advanced_features(test_user)
    first = _create_merchant("First Merchant")
    _create_merchant("Second Merchant")
    auth.login("testuser_1", "testpass")

    response = client.get(
        url_for("merchants.export_merchants"),
        query_string={"format": "json", "ids": str(first.id)},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0].get("name") == "First Merchant"
