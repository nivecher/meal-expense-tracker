"""Tests for merchant routes."""

from datetime import date
from decimal import Decimal

from flask import url_for

from app.auth.models import User
from app.expenses.models import Category, Expense
from app.extensions import db
from app.merchants.models import Merchant
from app.restaurants.models import Restaurant


def _enable_advanced_features(user: User) -> None:
    user.advanced_features_enabled = True
    db.session.add(user)
    db.session.commit()


def _create_merchant(name: str = "Acme Coffee") -> Merchant:
    merchant = Merchant(name=name, short_name="Acme", category="cafe_bakery", website="https://acme.example")
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


def test_import_merchants_page_loads(client, auth, test_user) -> None:
    """Merchant import page should render for advanced users."""
    _enable_advanced_features(test_user)
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("merchants.import_merchants"))

    assert response.status_code == 200
    assert b"Import Merchants" in response.data


def test_import_merchants_csv(client, auth, test_user) -> None:
    """Merchant import should create merchants from CSV uploads."""
    import io

    from werkzeug.datastructures import FileStorage

    _enable_advanced_features(test_user)
    auth.login("testuser_1", "testpass")

    csv_data = io.BytesIO(
        b"name,short_name,website,description,category,service_level,cuisine,menu_focus\n"
        b"Blue Baker,Blue Baker,https://bluebaker.example,Bakery cafe concept,deli_cafe,fast_casual,American,Bakery / Cafe\n"
    )
    file = FileStorage(stream=csv_data, filename="merchants.csv", content_type="text/csv")

    response = client.post(
        url_for("merchants.import_merchants"),
        data={"file": file},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Successfully imported 1 merchants." in response.data
    merchant = db.session.query(Merchant).filter_by(name="Blue Baker").one()
    assert merchant.short_name is None
    assert merchant.menu_focus == "Bakery / Cafe"


def test_new_merchant_form_shows_chain_toggle(client, auth, test_user) -> None:
    """Merchant form should expose chain status on the merchant, not restaurant, UI."""
    _enable_advanced_features(test_user)
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("merchants.new_merchant"))

    assert response.status_code == 200
    assert b"Chain Brand" in response.data


def test_edit_merchant_chain_suggestion_uses_current_user_restaurant_count(client, auth, test_user, test_user2) -> None:
    """Chain suggestion should count only the current user's linked restaurants."""
    _enable_advanced_features(test_user)
    _enable_advanced_features(test_user2)

    merchant = Merchant(name="Shared Merchant", short_name="Shared", category="standard_restaurant", is_chain=False)
    db.session.add(merchant)
    db.session.commit()

    db.session.add_all(
        [
            Restaurant(name="Shared One", city="Dallas", user_id=test_user.id, merchant_id=merchant.id, type="restaurant"),
            Restaurant(name="Shared Two", city="Plano", user_id=test_user.id, merchant_id=merchant.id, type="restaurant"),
            Restaurant(name="Other User One", city="Austin", user_id=test_user2.id, merchant_id=merchant.id, type="restaurant"),
            Restaurant(name="Other User Two", city="Houston", user_id=test_user2.id, merchant_id=merchant.id, type="restaurant"),
            Restaurant(name="Other User Three", city="Waco", user_id=test_user2.id, merchant_id=merchant.id, type="restaurant"),
            Restaurant(name="Other User Four", city="Irving", user_id=test_user2.id, merchant_id=merchant.id, type="restaurant"),
        ]
    )
    db.session.commit()

    auth.login("testuser_1", "testpass")
    response = client.get(url_for("merchants.edit_merchant", merchant_id=merchant.id))

    assert response.status_code == 200
    assert b"Suggested: mark as chain because 2 restaurant locations are linked." in response.data
    assert b"Suggested: mark as chain because 6 restaurant locations are linked." not in response.data


def test_view_merchant_shows_unlinked_matching_restaurants(client, auth, test_user) -> None:
    """Merchant detail should show unlinked restaurants matching name/short_name rules."""
    _enable_advanced_features(test_user)
    merchant = Merchant(name="Chili's Grill & Bar", short_name="Chili's", category="standard_restaurant")
    db.session.add(merchant)
    db.session.commit()

    matching = Restaurant(name="Chili's - Wylie", city="Wylie", user_id=test_user.id, type="restaurant")
    non_matching = Restaurant(name="Local Diner", city="Wylie", user_id=test_user.id, type="restaurant")
    db.session.add_all([matching, non_matching])
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("merchants.view_merchant", merchant_id=merchant.id))

    assert response.status_code == 200
    assert b"Unlinked Matches" in response.data
    assert b"Chili&#39;s - Wylie" in response.data
    assert b"Local Diner" not in response.data


def test_associate_matching_restaurants_links_selected_matches(client, auth, test_user) -> None:
    """POST action should link only selected matching restaurants to merchant."""
    _enable_advanced_features(test_user)
    merchant = Merchant(name="Chili's Grill & Bar", short_name="Chili's", category="standard_restaurant")
    db.session.add(merchant)
    db.session.commit()

    first_match = Restaurant(name="Chili's - Wylie", city="Wylie", user_id=test_user.id, type="restaurant")
    second_match = Restaurant(name="Chili's - Garland", city="Garland", user_id=test_user.id, type="restaurant")
    db.session.add_all([first_match, second_match])
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.post(
        url_for("merchants.associate_matching_restaurants", merchant_id=merchant.id),
        data={"restaurant_ids": [str(first_match.id)]},
        follow_redirects=True,
    )

    assert response.status_code == 200
    db.session.refresh(first_match)
    db.session.refresh(second_match)
    assert first_match.merchant_id == merchant.id
    assert second_match.merchant_id is None


def test_new_merchant_rejects_name_matching_existing_alias(client, auth, test_user) -> None:
    """Creating merchant should fail when name matches existing short name."""
    _enable_advanced_features(test_user)
    existing = Merchant(name="Acme Coffee", short_name="Acme", category="cafe_bakery")
    db.session.add(existing)
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.post(
        url_for("merchants.new_merchant"),
        data={"name": "Acme", "short_name": "Fresh", "category": "cafe_bakery"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Merchant name or alias already exists" in response.data
    assert db.session.query(Merchant).count() == 1


def test_new_merchant_rejects_alias_matching_existing_name(client, auth, test_user) -> None:
    """Creating merchant should fail when short name matches existing name."""
    _enable_advanced_features(test_user)
    existing = Merchant(name="Sunset Grill Group", short_name="Sunset", category="standard_restaurant")
    db.session.add(existing)
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.post(
        url_for("merchants.new_merchant"),
        data={"name": "Another Brand", "short_name": "Sunset Grill Group", "category": "other"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Merchant name or alias already exists" in response.data
    assert db.session.query(Merchant).count() == 1


def test_api_quick_add_merchant_persists_category(client, auth, test_user) -> None:
    """Quick-add API should accept and persist merchant category."""
    _enable_advanced_features(test_user)
    auth.login("testuser_1", "testpass")

    response = client.post(
        url_for("merchants.api_quick_add_merchant"),
        json={
            "name": "Blue Bottle Coffee",
            "short_name": "Blue Bottle",
            "category": "cafe_bakery",
            "website": "https://bluebottle.example",
        },
        headers={"X-CSRFToken": "dummy_csrf_token", "X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["merchant"]["category"] == "cafe_bakery"
    assert payload["merchant"]["category_display"] == "Deli / Cafe"

    merchant = db.session.query(Merchant).filter_by(name="Blue Bottle Coffee").one()
    assert merchant.category == "cafe_bakery"


def test_api_quick_add_merchant_drops_redundant_short_name(client, auth, test_user) -> None:
    """Quick-add should not persist a short name identical to the merchant name."""
    _enable_advanced_features(test_user)
    auth.login("testuser_1", "testpass")

    response = client.post(
        url_for("merchants.api_quick_add_merchant"),
        json={
            "name": "Blue Bottle Coffee",
            "short_name": "Blue Bottle Coffee",
            "category": "cafe_bakery",
        },
        headers={"X-CSRFToken": "dummy_csrf_token", "X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["merchant"]["short_name"] is None

    merchant = db.session.query(Merchant).filter_by(name="Blue Bottle Coffee").one()
    assert merchant.short_name is None


def test_api_suggest_merchant_returns_best_match(client, auth, test_user) -> None:
    """Suggestion API should return the best merchant for a matching restaurant name."""
    _enable_advanced_features(test_user)
    merchant = Merchant(name="Chili's Grill & Bar", short_name="Chili's", category="standard_restaurant")
    db.session.add(merchant)
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.get(
        url_for("merchants.api_suggest_merchant"),
        query_string={"restaurant_name": "Chili's - Wylie"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["merchant"]["id"] == merchant.id
    assert payload["merchant"]["category"] == "standard_restaurant"
    assert payload["merchant"]["category_display"] == "Standard Restaurant"


def test_list_merchants_shows_expense_rollups(client, auth, test_user) -> None:
    """Merchant list should show expense totals and counts."""
    _enable_advanced_features(test_user)
    merchant = Merchant(name="Acme Coffee", short_name="Acme", category="cafe_bakery")
    db.session.add(merchant)
    db.session.flush()

    restaurant = Restaurant(
        name="Acme - Downtown",
        city="Dallas",
        user_id=test_user.id,
        type="restaurant",
        merchant_id=merchant.id,
    )
    category = Category(name="Meals", user_id=test_user.id)
    db.session.add_all([restaurant, category])
    db.session.flush()

    expense = Expense(
        amount=Decimal("18.50"),
        notes="Lunch",
        date=date.today(),
        restaurant_id=restaurant.id,
        category_id=category.id,
        user_id=test_user.id,
    )
    db.session.add(expense)
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("merchants.list_merchants"))

    assert response.status_code == 200
    assert b"18.50" in response.data
    assert b"expenses" in response.data
    assert b"Add Restaurant" in response.data
    assert b"Review Associations" in response.data


def test_view_merchant_shows_expense_summary(client, auth, test_user) -> None:
    """Merchant detail should show aggregate spend and expense metrics."""
    _enable_advanced_features(test_user)
    merchant = Merchant(name="Acme Coffee", short_name="Acme", category="cafe_bakery")
    db.session.add(merchant)
    db.session.flush()

    restaurant = Restaurant(
        name="Acme - Downtown",
        city="Dallas",
        user_id=test_user.id,
        type="restaurant",
        merchant_id=merchant.id,
    )
    category = Category(name="Meals", user_id=test_user.id)
    db.session.add_all([restaurant, category])
    db.session.flush()

    expense = Expense(
        amount=Decimal("24.00"),
        notes="Dinner",
        date=date.today(),
        restaurant_id=restaurant.id,
        category_id=category.id,
        user_id=test_user.id,
    )
    db.session.add(expense)
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("merchants.view_merchant", merchant_id=merchant.id))

    assert response.status_code == 200
    assert b"Total Spend" in response.data
    assert b"24.00" in response.data
    assert b"Average Expense" in response.data


def test_review_restaurant_associations_shows_suggestions(client, auth, test_user) -> None:
    """Association review page should show unlinked restaurants with suggestions."""
    _enable_advanced_features(test_user)
    merchant = Merchant(name="Chili's Grill & Bar", short_name="Chili's", category="standard_restaurant")
    db.session.add(merchant)
    db.session.flush()

    matching = Restaurant(name="Chili's - Wylie", city="Wylie", user_id=test_user.id, type="restaurant")
    no_match = Restaurant(name="Local Diner", city="Dallas", user_id=test_user.id, type="restaurant")
    db.session.add_all([matching, no_match])
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("merchants.review_restaurant_associations"))

    assert response.status_code == 200
    assert b"Associate Restaurants to Merchants" in response.data
    assert b"Chili&#39;s Grill &amp; Bar" in response.data
    assert b"No strong suggestion" in response.data
    assert b"Create Merchant" in response.data


def test_apply_suggested_restaurant_associations_links_matches(client, auth, test_user) -> None:
    """Bulk apply should link restaurants with strong suggestions."""
    _enable_advanced_features(test_user)
    merchant = Merchant(name="Chili's Grill & Bar", short_name="Chili's", category="standard_restaurant")
    db.session.add(merchant)
    db.session.flush()

    matching = Restaurant(name="Chili's - Wylie", city="Wylie", user_id=test_user.id, type="restaurant")
    no_match = Restaurant(name="Local Diner", city="Dallas", user_id=test_user.id, type="restaurant")
    db.session.add_all([matching, no_match])
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.post(
        url_for("merchants.apply_suggested_restaurant_associations"),
        data={"restaurant_ids": [str(matching.id)]},
        follow_redirects=True,
    )

    assert response.status_code == 200
    db.session.refresh(matching)
    db.session.refresh(no_match)
    assert matching.merchant_id == merchant.id
    assert no_match.merchant_id is None


def test_list_merchants_shows_missing_data_ctas(client, auth, test_user) -> None:
    """Merchant list should surface missing restaurants and missing merchant CTAs."""
    _enable_advanced_features(test_user)
    empty_merchant = Merchant(name="Sunset Grill Group", short_name="Sunset", category="standard_restaurant")
    suggested_merchant = Merchant(name="Chili's Grill & Bar", short_name="Chili's", category="standard_restaurant")
    db.session.add_all([empty_merchant, suggested_merchant])
    db.session.flush()

    unlinked = Restaurant(name="Chili's - Wylie", city="Wylie", user_id=test_user.id, type="restaurant")
    db.session.add(unlinked)
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("merchants.list_merchants"))

    assert response.status_code == 200
    assert b"merchant" in response.data
    assert b"without restaurants" in response.data
    assert b"still need a merchant" in response.data
    assert b"suggestion ready" in response.data
    assert b"Review 1 suggestion" in response.data
    assert b"Filter Missing Restaurants" in response.data


def test_list_merchants_filters_by_new_fields(client, auth, test_user) -> None:
    """Merchant list filters should support cuisine, menu focus, and description presence."""
    _enable_advanced_features(test_user)
    first = Merchant(
        name="Blue Baker",
        category="cafe_bakery",
        cuisine="American",
        menu_focus="Bakery / Cafe",
        description="Bakery-cafe concept",
    )
    second = Merchant(
        name="Pei Wei Asian Kitchen",
        category="standard_restaurant",
        cuisine="Asian",
        menu_focus="Fusion",
        description=None,
    )
    db.session.add_all([first, second])
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.get(
        url_for("merchants.list_merchants"),
        query_string={
            "cuisine": "American",
            "menu_focus": "Bakery / Cafe",
            "has_description": "yes",
        },
    )

    assert response.status_code == 200
    assert b"Blue Baker" in response.data
    assert b"Pei Wei Asian Kitchen" not in response.data


def test_list_merchants_filters_by_chain_status(client, auth, test_user) -> None:
    """Merchant list should filter by chain versus independent status."""
    _enable_advanced_features(test_user)
    chain = Merchant(name="Blue Baker", is_chain=True)
    independent = Merchant(name="Local Spot", is_chain=False)
    db.session.add_all([chain, independent])
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("merchants.list_merchants"), query_string={"is_chain": "true"})

    assert response.status_code == 200
    assert b"Blue Baker" in response.data
    assert b"Local Spot" not in response.data


def test_list_merchants_filters_missing_restaurants(client, auth, test_user) -> None:
    """Merchant list should support filtering to merchants without restaurants."""
    _enable_advanced_features(test_user)
    merchant_without_restaurants = Merchant(name="Brand Only")
    merchant_with_restaurants = Merchant(name="Blue Baker")
    db.session.add_all([merchant_without_restaurants, merchant_with_restaurants])
    db.session.flush()
    db.session.add(Restaurant(name="Blue Baker - Frisco", city="Frisco", user_id=test_user.id, merchant_id=merchant_with_restaurants.id))
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("merchants.list_merchants"), query_string={"restaurant_status": "without_restaurants"})

    assert response.status_code == 200
    assert b"Brand Only" in response.data
    assert b"Blue Baker - Frisco" not in response.data
    assert b"Restaurants: Missing Restaurants" in response.data


def test_list_merchants_shows_chain_suggestion_for_multiple_locations(client, auth, test_user) -> None:
    """Merchant list should suggest chain status when multiple restaurants are linked."""
    _enable_advanced_features(test_user)
    merchant = Merchant(name="Blue Baker", is_chain=False)
    db.session.add(merchant)
    db.session.flush()
    db.session.add_all(
        [
            Restaurant(name="Blue Baker - Frisco", city="Frisco", user_id=test_user.id, merchant_id=merchant.id),
            Restaurant(name="Blue Baker - Denton", city="Denton", user_id=test_user.id, merchant_id=merchant.id),
        ]
    )
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("merchants.list_merchants"))

    assert response.status_code == 200
    assert b"Suggest Chain: 2 locations" in response.data


def test_list_merchants_search_matches_menu_focus(client, auth, test_user) -> None:
    """Merchant search should include menu focus values."""
    _enable_advanced_features(test_user)
    first = Merchant(name="Blue Baker", menu_focus="Bakery / Cafe")
    second = Merchant(name="Pei Wei Asian Kitchen", menu_focus="Fusion")
    db.session.add_all([first, second])
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("merchants.list_merchants"), query_string={"q": "Fusion"})

    assert response.status_code == 200
    assert b"Pei Wei Asian Kitchen" in response.data
    assert b"Blue Baker" not in response.data


def test_list_merchants_shows_description_and_applied_filter_summary(client, auth, test_user) -> None:
    """Merchant cards should show descriptions and filtered pages should show applied filter summaries."""
    _enable_advanced_features(test_user)
    merchant = Merchant(
        name="Blue Baker",
        category="deli_cafe",
        cuisine="American",
        menu_focus="Bakery / Cafe",
        description="Bakery-cafe concept",
    )
    db.session.add(merchant)
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.get(
        url_for("merchants.list_merchants"),
        query_string={"q": "Blue", "menu_focus": "Bakery / Cafe"},
    )

    assert response.status_code == 200
    assert b"Bakery-cafe concept" in response.data
    assert b"Search: Blue" in response.data
    assert b"Menu Focus: Bakery / Cafe" in response.data
    assert b"Clear filters" in response.data


def test_list_merchants_filter_picklists_only_show_used_values(client, auth, test_user) -> None:
    """Merchant list filter picklists should be based on values currently present in merchant rows."""
    _enable_advanced_features(test_user)
    db.session.add_all(
        [
            Merchant(name="Blue Baker", category="deli_cafe", service_level="fast_casual"),
            Merchant(name="Panda Express", category="mall_food_court", service_level="quick_service"),
        ]
    )
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("merchants.list_merchants"))

    assert response.status_code == 200
    assert b'value="deli_cafe"' in response.data
    assert b'value="mall_food_court"' in response.data
    assert b'value="standard_restaurant"' not in response.data
    assert b'value="fast_casual"' in response.data
    assert b'value="quick_service"' in response.data
    assert b'value="casual_dining"' not in response.data


def test_delete_merchant_keeps_restaurants_and_unlinks_them(client, auth, test_user) -> None:
    """Deleting a merchant should preserve linked restaurants and clear merchant_id."""
    _enable_advanced_features(test_user)
    merchant = Merchant(name="Acme Coffee", short_name="Acme", category="cafe_bakery")
    db.session.add(merchant)
    db.session.flush()

    restaurant = Restaurant(
        name="Acme - Downtown",
        city="Dallas",
        user_id=test_user.id,
        type="restaurant",
        merchant_id=merchant.id,
    )
    db.session.add(restaurant)
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.post(url_for("merchants.delete_merchant", merchant_id=merchant.id))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"

    db.session.expire_all()
    preserved_restaurant = db.session.get(Restaurant, restaurant.id)
    assert preserved_restaurant is not None
    assert preserved_restaurant.merchant_id is None
    assert db.session.get(Merchant, merchant.id) is None
