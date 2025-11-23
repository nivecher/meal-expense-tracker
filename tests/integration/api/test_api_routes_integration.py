"""Simple integration tests for API routes using Flask test client."""

from flask.testing import FlaskClient

from app.auth.models import User
from app.expenses.models import Category


class TestAPIRoutesSimple:
    """Simple integration tests for API routes."""

    def test_health_check(self, client: FlaskClient):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json["status"] == "healthy"

    def test_version_info(self, client: FlaskClient):
        """Test version info endpoint."""
        response = client.get("/api/v1/version")
        assert response.status_code == 200
        assert response.json["status"] == "success"
        assert "version" in response.json["data"]

    def test_get_cuisines(self, client: FlaskClient):
        """Test getting cuisines."""
        response = client.get("/api/v1/cuisines")
        assert response.status_code == 200
        assert response.json["status"] == "success"

    def test_get_expenses_requires_auth(self, client: FlaskClient):
        """Test that getting expenses requires authentication."""
        response = client.get("/api/v1/expenses")
        assert response.status_code == 401

    def test_get_expenses_with_auth(self, client: FlaskClient, auth, test_user: User):
        """Test getting expenses with authentication."""
        # Log in the test user
        auth.login("testuser_1", "testpass")

        response = client.get("/api/v1/expenses")
        assert response.status_code == 200
        assert response.json["status"] == "success"
        assert "data" in response.json

    def test_create_expense_requires_auth(self, client: FlaskClient):
        """Test that creating expenses requires authentication."""
        response = client.post("/api/v1/expenses", json={"amount": 25.50, "description": "Test"})
        assert response.status_code == 401

    def test_create_expense_with_auth(self, client: FlaskClient, auth, test_user: User):
        """Test creating expense with authentication."""
        # Log in the test user
        auth.login("testuser_1", "testpass")

        # Create a category first
        category = Category(name="Test Category", color="#FF5733", user_id=test_user.id)
        from app.extensions import db

        db.session.add(category)
        db.session.commit()

        response = client.post(
            "/api/v1/expenses",
            json={
                "amount": 25.50,
                "restaurant_id": 1,  # Add required restaurant_id
                "category_id": category.id,
                "date": "2024-01-01",
            },
        )

        assert response.status_code == 201
        assert response.json["status"] == "success"
        assert "data" in response.json

    def test_get_restaurants_requires_auth(self, client: FlaskClient):
        """Test that getting restaurants requires authentication."""
        response = client.get("/api/v1/restaurants")
        assert response.status_code == 401

    def test_get_restaurants_with_auth(self, client: FlaskClient, auth, test_user: User):
        """Test getting restaurants with authentication."""
        # Log in the test user
        auth.login("testuser_1", "testpass")

        response = client.get("/api/v1/restaurants")
        assert response.status_code == 200
        assert response.json["status"] == "success"
        assert "data" in response.json

    def test_create_restaurant_with_auth(self, client: FlaskClient, auth, test_user: User):
        """Test creating restaurant with authentication."""
        # Log in the test user
        auth.login("testuser_1", "testpass")

        response = client.post(
            "/api/v1/restaurants",
            json={
                "name": "Test Restaurant",
                "address": "123 Test St",
                "city": "Test City",
                "state": "TS",
                "postal_code": "12345",
            },
        )

        assert response.status_code == 201
        assert response.json["status"] == "success"
        assert "data" in response.json

    def test_get_categories_requires_auth(self, client: FlaskClient):
        """Test that getting categories requires authentication."""
        response = client.get("/api/v1/categories")
        assert response.status_code == 401

    def test_get_categories_with_auth(self, client: FlaskClient, auth, test_user: User):
        """Test getting categories with authentication."""
        # Log in the test user
        auth.login("testuser_1", "testpass")

        response = client.get("/api/v1/categories")
        assert response.status_code == 200
        assert response.json["status"] == "success"
        assert "data" in response.json

    def test_create_category_with_auth(self, client: FlaskClient, auth, test_user: User):
        """Test creating category with authentication."""
        # Log in the test user
        auth.login("testuser_1", "testpass")

        response = client.post("/api/v1/categories", json={"name": "Test Category", "color": "#FF5733"})
        assert response.status_code == 201
        assert response.json["status"] == "success"
        assert "data" in response.json

    def test_validate_restaurant_requires_auth(self, client: FlaskClient):
        """Test that validating restaurants requires authentication."""
        response = client.post(
            "/api/v1/restaurants/validate", json={"name": "Test Restaurant", "address": "123 Test St"}
        )
        assert response.status_code == 401

    def test_validate_restaurant_with_auth(self, client: FlaskClient, auth, test_user: User):
        """Test validating restaurant with authentication."""
        # Log in the test user
        auth.login("testuser_1", "testpass")

        # First create a restaurant to validate
        create_response = client.post(
            "/api/v1/restaurants",
            json={
                "name": "Test Restaurant",
                "address": "123 Test St",
                "city": "Test City",
                "state": "TS",
                "postal_code": "12345",
            },
        )

        if create_response.status_code == 201:
            restaurant_id = create_response.json["data"]["id"]

            response = client.post(
                "/api/v1/restaurants/validate",
                json={"restaurant_id": restaurant_id, "google_place_id": "test_place_id_123"},
            )

            # Validation may fail due to missing Google Maps API key in test environment
            assert response.status_code in [200, 400]
            if response.status_code == 200:
                assert response.json["status"] == "success"
                assert "data" in response.json
            else:
                # Expected failure due to missing API key
                assert response.json["status"] == "error"

    def test_check_restaurant_exists_requires_auth(self, client: FlaskClient):
        """Test that checking restaurant existence requires authentication."""
        response = client.get("/api/v1/restaurants/check?place_id=test_place_id")
        assert response.status_code == 401

    def test_check_restaurant_exists_with_auth(self, client: FlaskClient, auth, test_user: User):
        """Test checking restaurant existence with authentication."""
        # Log in the test user
        auth.login("testuser_1", "testpass")

        response = client.get("/api/v1/restaurants/check?place_id=test_place_id")
        assert response.status_code == 200
        assert response.json["status"] == "success"
        assert "data" in response.json

    def test_api_error_handling(self, client: FlaskClient, auth, test_user: User):
        """Test API error handling."""
        # Log in the test user
        auth.login("testuser_1", "testpass")

        # Test invalid expense data
        response = client.post("/api/v1/expenses", json={"amount": "invalid", "description": "Test"})
        assert response.status_code == 400
        assert response.json["status"] == "error"

    def test_api_not_found(self, client: FlaskClient, auth, test_user: User):
        """Test API 404 handling."""
        # Log in the test user
        auth.login("testuser_1", "testpass")

        # Test getting non-existent expense
        response = client.get("/api/v1/expenses/99999")
        assert response.status_code == 404
        assert response.json["status"] == "error"
