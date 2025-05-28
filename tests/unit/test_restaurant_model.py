import pytest
from app import Restaurant, db
from tests.factories import RestaurantFactory, UserFactory

@pytest.mark.unit
def test_restaurant_creation():
    """Test restaurant creation with factory."""
    restaurant = RestaurantFactory()
    assert restaurant.name is not None
    assert restaurant.address is not None
    assert restaurant.category in ['restaurant', 'cafe', 'fast_food']
    assert restaurant.chain is not None
    assert restaurant.description is not None

@pytest.mark.unit
def test_restaurant_repr():
    """Test restaurant string representation."""
    restaurant = RestaurantFactory()
    assert str(restaurant) == f'<Restaurant {restaurant.name}>'

@pytest.mark.unit
def test_restaurant_unique_name(auth_client):
    """Test that restaurant names must be unique."""
    with auth_client.application.app_context():
        # Create first restaurant
        restaurant1 = RestaurantFactory()
        db.session.add(restaurant1)
        db.session.commit()
        
        # Try to create second restaurant with same name
        restaurant2 = RestaurantFactory(name=restaurant1.name)
        db.session.add(restaurant2)
        
        with pytest.raises(Exception):  # Should raise an integrity error
            db.session.commit()
        
        db.session.rollback()

@pytest.mark.unit
def test_restaurant_expenses_relationship(auth_client):
    """Test the relationship between restaurants and expenses."""
    with auth_client.application.app_context():
        user = UserFactory()
        restaurant = RestaurantFactory()
        db.session.add_all([user, restaurant])
        db.session.commit()
        
        # Create some expenses for the restaurant
        from tests.factories import ExpenseFactory
        expenses = [
            ExpenseFactory(restaurant=restaurant, user=user)
            for _ in range(3)
        ]
        db.session.add_all(expenses)
        db.session.commit()
        
        # Verify the relationship
        assert len(restaurant.expenses.all()) == 3
        for expense in restaurant.expenses:
            assert expense.restaurant_id == restaurant.id
            assert expense.user_id == user.id 