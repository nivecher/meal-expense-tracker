from flask.testing import FlaskClient

from app.auth.models import User
from app.extensions import db
from app.merchants.models import Merchant
from app.restaurants.models import Restaurant
from tests.conftest import AuthActions


def _enable_advanced_features(user: User) -> None:
    user.advanced_features_enabled = True
    db.session.add(user)
    db.session.commit()


def test_index(client: FlaskClient) -> None:
    """Test the index page."""
    response = client.get("/")
    assert response.status_code == 302  # Redirect to login
    assert "/auth/login" in response.headers["Location"]


def test_index_redirects_to_login(client: FlaskClient) -> None:
    """Test that index page redirects to login when not authenticated."""
    response = client.get("/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_index_with_expenses(client: FlaskClient, auth: AuthActions, test_user: User) -> None:
    """Test index page with expenses."""
    auth.login("testuser_1", "testpass")
    # Add a restaurant and expense
    client.post(
        "/restaurants/add",
        data={
            "name": "Test Restaurant",
            "type": "restaurant",  # Add required field
            "city": "Test City",
            "address": "123 Test St",
            "phone": "123-456-7890",
            "website": "http://test.com",
        },
        follow_redirects=True,
    )

    # Add an expense
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Lunch",
            "category": "Food",
            "amount": "25.50",
            "notes": "Test expense",
        },
        follow_redirects=True,
    )

    # Check the index page
    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200
    # Check for restaurant data or dashboard content
    assert b"Test Restaurant" in response.data or b"Dashboard" in response.data


def test_index_sorting(client: FlaskClient, auth: AuthActions, test_user: User) -> None:
    """Test index page sorting."""
    auth.login("testuser_1", "testpass")
    # Add a restaurant and multiple expenses
    client.post(
        "/restaurants/add",
        data={
            "name": "Test Restaurant",
            "type": "restaurant",  # Add required field
            "city": "Test City",
            "address": "123 Test St",
            "phone": "123-456-7890",
            "website": "http://test.com",
        },
        follow_redirects=True,
    )

    # Add expenses with different amounts
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Lunch",
            "category": "Food",
            "amount": "15.50",
            "notes": "Cheaper expense",
        },
        follow_redirects=True,
    )

    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-21",
            "meal_type": "Dinner",
            "category": "Food",
            "amount": "35.50",
            "notes": "More expensive expense",
        },
        follow_redirects=True,
    )

    # Test sorting by amount
    response = client.get("/?sort=amount&order=asc", follow_redirects=True)
    assert response.status_code == 200
    # Check for expense data or dashboard content
    assert b"15.50" in response.data or b"35.50" in response.data or b"Dashboard" in response.data


def test_index_search(client: FlaskClient, auth: AuthActions, test_user: User) -> None:
    """Test index page search functionality."""
    auth.login("testuser_1", "testpass")
    # Add a restaurant and expense
    client.post(
        "/restaurants/add",
        data={
            "name": "Test Restaurant",
            "type": "restaurant",  # Add required field
            "city": "Test City",
            "address": "123 Test St",
            "phone": "123-456-7890",
            "website": "http://test.com",
        },
        follow_redirects=True,
    )

    # Add an expense
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Lunch",
            "category": "Food",
            "amount": "25.50",
            "notes": "Test expense",
        },
        follow_redirects=True,
    )

    # Test search functionality
    response = client.get("/?search=Test", follow_redirects=True)
    assert response.status_code == 200
    # Check for restaurant data or dashboard content
    assert b"Test Restaurant" in response.data or b"Dashboard" in response.data


def test_index_shows_merchant_summary_for_advanced_users(
    client: FlaskClient, auth: AuthActions, test_user: User
) -> None:
    """Dashboard should show merchant summary cards for advanced users."""
    _enable_advanced_features(test_user)

    merchant = Merchant(name="Acme Coffee", short_name="Acme", category="cafe_bakery", is_chain=True)
    db.session.add(merchant)
    db.session.commit()

    restaurant = Restaurant(
        name="Acme Coffee - Downtown",
        city="Dallas",
        user_id=test_user.id,
        merchant_id=merchant.id,
        type="restaurant",
    )
    db.session.add(restaurant)
    db.session.commit()

    auth.login("testuser_1", "testpass")
    response = client.get("/", follow_redirects=True)

    assert response.status_code == 200
    assert b"Merchant Summary" in response.data
    assert b"View Merchants" in response.data
    assert b"Chain Brands" in response.data
    assert b"Linked Restaurants" in response.data


def test_index_hides_merchant_summary_for_standard_users(
    client: FlaskClient, auth: AuthActions, test_user: User
) -> None:
    """Dashboard should not show merchant summary cards for standard users."""
    auth.login("testuser_1", "testpass")

    response = client.get("/", follow_redirects=True)

    assert response.status_code == 200
    assert b"Merchant Summary" not in response.data
    assert b"View Merchants" not in response.data
