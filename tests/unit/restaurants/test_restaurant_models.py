"""Tests for restaurant models."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.restaurants.models import Restaurant


def test_create_restaurant(session, test_user) -> None:
    """Test creating a new restaurant."""
    restaurant = Restaurant(
        user_id=test_user.id,
        name="Test Restaurant",
        city="Test City",
        address_line_1="123 Test St",  # Use address_line_1 instead of address
        phone="123-456-7890",
        website="http://test.com",
        cuisine="American",
        type="restaurant",  # Add required field
    )

    session.add(restaurant)
    session.commit()

    assert restaurant.id is not None
    assert restaurant.name == "Test Restaurant"
    assert restaurant.city == "Test City"
    assert restaurant.phone == "123-456-7890"
    assert restaurant.website == "http://test.com"
    assert restaurant.cuisine == "American"
    assert restaurant.user_id == test_user.id


def test_restaurant_required_fields(session, test_user) -> None:
    """Test that required fields are enforced."""
    # Missing name
    with pytest.raises(IntegrityError):
        restaurant = Restaurant(user_id=test_user.id, city="Test City", type="restaurant")
        session.add(restaurant)
        session.commit()

    session.rollback()

    # Missing user_id
    with pytest.raises(IntegrityError):
        restaurant = Restaurant(name="Test Restaurant", city="Test City", type="restaurant")
        session.add(restaurant)
        session.commit()


def test_restaurant_uniqueness(session, test_user) -> None:
    """Test that restaurant names are unique per user and city."""
    # Create first restaurant
    restaurant1 = Restaurant(
        user_id=test_user.id,
        name="Test Restaurant",
        city="Test City",
        type="restaurant",  # Add required field
    )
    session.add(restaurant1)
    session.commit()

    # Try to create a restaurant with the same name and city
    with pytest.raises(IntegrityError):
        restaurant2 = Restaurant(
            user_id=test_user.id,
            name="Test Restaurant",
            city="Test City",
            type="restaurant",  # Add required field
        )
        session.add(restaurant2)
        session.commit()

    session.rollback()

    # Different name should be fine
    restaurant3 = Restaurant(
        user_id=test_user.id,
        name="Different Restaurant",
        city="Test City",
        type="restaurant",  # Add required field
    )
    session.add(restaurant3)
    session.commit()
    assert restaurant3.id is not None


def test_restaurant_relationships(session, test_user, test_expense) -> None:
    """Test relationships with other models."""
    # Test relationship with user
    assert test_expense.restaurant.user_id == test_user.id
    assert test_expense.restaurant in test_expense.user.restaurants

    # Test relationship with expenses
    assert len(test_expense.restaurant.expenses) == 1
    assert test_expense in test_expense.restaurant.expenses


def test_restaurant_properties(test_restaurant) -> None:
    """Test computed properties."""
    # Test full_name property with city
    assert test_restaurant.full_name == f"{test_restaurant.name} - {test_restaurant.city}"

    # Test with missing city
    test_restaurant.city = None
    assert test_restaurant.full_name == test_restaurant.name

    # Test with empty string city
    test_restaurant.city = ""
    assert test_restaurant.full_name == test_restaurant.name

    # Test with whitespace city
    test_restaurant.city = "  "
    assert test_restaurant.full_name == test_restaurant.name


def test_restaurant_string_representation(test_restaurant) -> None:
    """Test the string representation of a restaurant."""
    assert str(test_restaurant) == f"<Restaurant {test_restaurant.name}>"


def test_restaurant_serialization(test_restaurant) -> None:
    """Test that a restaurant can be serialized to a dictionary."""
    serialized = test_restaurant.to_dict()
    assert isinstance(serialized, dict)
    assert serialized["name"] == test_restaurant.name
    assert serialized["city"] == test_restaurant.city
    assert "created_at" in serialized
    assert "updated_at" in serialized


def test_restaurant_expenses_relationship(test_restaurant, test_expense) -> None:
    """Test the expenses relationship."""
    assert test_expense in test_restaurant.expenses
    assert test_expense.restaurant == test_restaurant
    assert test_restaurant.expenses[0].id == test_expense.id
