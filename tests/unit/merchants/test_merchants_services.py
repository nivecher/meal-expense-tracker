"""Tests for merchant service helpers."""

from app import create_app
from app.auth.models import User
from app.extensions import db
from app.merchants import services as merchant_services
from app.merchants.models import Merchant
from app.merchants.services import find_merchant_for_restaurant, get_create_merchant_prefill_for_restaurant
from app.restaurants.models import Restaurant


def test_find_merchant_for_restaurant_prefers_website_domain() -> None:
    """Merchant matching should use website domain before restaurant name rules."""
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        user = User(username="merchantmatch", email="merchantmatch@example.com", password_hash="hash")
        db.session.add(user)
        db.session.flush()

        merchant = Merchant(
            name="Starbucks",
            short_name="Starbucks",
            category="cafe_bakery",
            website="https://www.starbucks.com/",
        )
        db.session.add(merchant)
        db.session.commit()

        matched = find_merchant_for_restaurant(
            restaurant_name="Reserve Roastery Location",
            website="https://starbucks.com/store-locator?store=123",
        )

        assert matched is not None
        assert matched.id == merchant.id

        db.drop_all()


def test_get_create_merchant_prefill_for_restaurant_uses_brand_name_and_apex_website() -> None:
    """Merchant create prefills should leave redundant short names blank."""
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        user = User(username="merchantprefill", email="merchantprefill@example.com", password_hash="hash")
        db.session.add(user)
        db.session.flush()

        restaurant = Restaurant(
            name="Blue Bottle Coffee - Downtown",
            city="Dallas",
            user_id=user.id,
            type="coffee_shop",
            website="https://locations.bluebottlecoffee.com/cafes/downtown?ref=maps",
            service_level="fast_casual",
        )

        prefill = get_create_merchant_prefill_for_restaurant(restaurant)

        assert prefill["name"] == "Blue Bottle Coffee"
        assert prefill["short_name"] == ""
        assert prefill["website"] == "https://bluebottlecoffee.com"
        assert prefill["category"] == "deli_cafe"
        assert prefill["service_level"] == "fast_casual"

        db.drop_all()


def test_get_create_merchant_prefill_uses_website_subset_for_short_name() -> None:
    """Merchant create prefills should use a website-derived subset with merchant casing."""
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        user = User(username="merchantsubset", email="merchantsubset@example.com", password_hash="hash")
        db.session.add(user)
        db.session.flush()

        restaurant = Restaurant(
            name="Red Robin Gourmet Burgers and Brews - Plano",
            city="Plano",
            user_id=user.id,
            type="restaurant",
            website="https://www.redrobin.com/menu/burgers",
        )

        prefill = get_create_merchant_prefill_for_restaurant(restaurant)

        assert prefill["name"] == "Red Robin Gourmet Burgers and Brews"
        assert prefill["short_name"] == "Red Robin"
        assert prefill["website"] == "https://redrobin.com"
        assert prefill["category"] == "standard_restaurant"

        db.drop_all()


def test_get_merchant_categories_expose_format_options_with_slashes() -> None:
    """Merchant categories should expose the new format category options."""
    categories = merchant_services.get_merchant_categories()

    assert categories[0] == "standard_restaurant"
    assert "deli_cafe" in categories
    assert "bakery_specialty" in categories
    assert "kiosk_pop_up" in categories
    assert "clubhouse_private_venue" in categories
    assert merchant_services.get_merchant_format_category_label("deli_cafe") == "Deli / Cafe"
    assert merchant_services.get_merchant_format_category_label("bakery_specialty") == "Bakery / Specialty"
    assert merchant_services.get_merchant_format_category_label("kiosk_pop_up") == "Kiosk / Pop-Up"
    assert merchant_services.get_merchant_format_category_label("pub_tavern_bar") == "Pub / Tavern / Bar"


def test_get_merchant_format_category_groups_include_headings_and_definitions() -> None:
    """Grouped format category metadata should include the documented headings and definitions."""
    groups = merchant_services.get_merchant_format_category_groups()

    assert groups[0]["label"] == "Traditional Physical Formats"
    assert any(option["value"] == "deli_cafe" for option in groups[1]["options"])
    assert any(option["value"] == "bakery_specialty" for option in groups[1]["options"])
    assert any(option["value"] == "dinner_theater_cinema" for option in groups[3]["options"])
    assert any("drive-through" in option["definition"] for option in groups[0]["options"])
    assert any("cold-prep service" in option["definition"] for option in groups[1]["options"])


def test_get_unique_merchant_filter_picklists_only_include_used_values() -> None:
    """Merchant filter picklists should only expose values currently present in merchant rows."""
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        db.session.add_all(
            [
                Merchant(name="Blue Baker", category="deli_cafe", service_level="fast_casual"),
                Merchant(name="Panda Express", category="mall_food_court", service_level="quick_service"),
            ]
        )
        db.session.commit()

        assert merchant_services.get_unique_merchant_categories() == ["deli_cafe", "mall_food_court"]
        assert merchant_services.get_unique_merchant_service_levels() == ["fast_casual", "quick_service"]

        db.drop_all()


def test_infer_merchant_category_from_restaurant_uses_format_categories() -> None:
    """Restaurant type inference should map into merchant format categories."""
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        user = User(username="merchantinfer", email="merchantinfer@example.com", password_hash="hash")
        db.session.add(user)
        db.session.flush()

        donut_restaurant = Restaurant(name="Daily Donuts", user_id=user.id, type="donut_shop")
        sandwich_restaurant = Restaurant(name="Sub Stop", user_id=user.id, type="sandwich_shop")
        generic_restaurant = Restaurant(name="Neighborhood Grill", user_id=user.id, type="restaurant")

        assert merchant_services.infer_merchant_category_from_restaurant(donut_restaurant) == "bakery_specialty"
        assert merchant_services.infer_merchant_category_from_restaurant(sandwich_restaurant) == "deli_cafe"
        assert merchant_services.infer_merchant_category_from_restaurant(generic_restaurant) == "standard_restaurant"

        db.drop_all()


def test_create_merchant_drops_redundant_short_name() -> None:
    """Redundant short names should not be persisted."""
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        user = User(username="merchantcreate", email="merchantcreate@example.com", password_hash="hash")
        db.session.add(user)
        db.session.flush()

        merchant = merchant_services.create_merchant(
            user.id,
            {
                "name": "Blue Bottle Coffee",
                "short_name": " blue bottle   coffee ",
                "category": "cafe_bakery",
            },
        )

        assert merchant.short_name is None

        db.drop_all()


def test_update_merchant_drops_redundant_short_name() -> None:
    """Updating a merchant should clear a short name that matches the name."""
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        merchant = Merchant(name="Acme Coffee", short_name="Acme", category="cafe_bakery")
        db.session.add(merchant)
        db.session.commit()

        updated = merchant_services.update_merchant(
            merchant.id,
            {
                "name": "Acme Coffee",
                "short_name": "Acme Coffee",
            },
        )

        assert updated is not None
        assert updated.short_name is None
        assert updated.category == "cafe_bakery"

        db.drop_all()


def test_create_and_update_merchant_persist_is_chain() -> None:
    """Merchant create/update should persist the chain flag."""
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        user = User(username="merchantchain", email="merchantchain@example.com", password_hash="hash")
        db.session.add(user)
        db.session.flush()

        merchant = merchant_services.create_merchant(
            user.id,
            {
                "name": "Chain Brand",
                "is_chain": True,
            },
        )
        assert merchant.is_chain is True

        updated = merchant_services.update_merchant(merchant.id, {"is_chain": False})
        assert updated is not None
        assert updated.is_chain is False

        db.drop_all()


def test_delete_merchant_unlinks_restaurants_without_deleting_them() -> None:
    """Deleting a merchant should preserve linked restaurants and just clear merchant_id."""
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        user = User(username="merchantdelete", email="merchantdelete@example.com", password_hash="hash")
        db.session.add(user)
        db.session.flush()

        merchant = Merchant(name="Acme Coffee", category="cafe_bakery")
        db.session.add(merchant)
        db.session.flush()

        restaurant = Restaurant(name="Acme - Downtown", user_id=user.id, merchant_id=merchant.id)
        db.session.add(restaurant)
        db.session.commit()

        deleted = merchant_services.delete_merchant(merchant.id)

        assert deleted is True
        preserved_restaurant = db.session.get(Restaurant, restaurant.id)
        assert preserved_restaurant is not None
        assert preserved_restaurant.merchant_id is None
        assert db.session.get(Merchant, merchant.id) is None

        db.drop_all()
