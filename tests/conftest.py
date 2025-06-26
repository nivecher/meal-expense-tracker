"""Pytest configuration and fixtures for the application."""

import os
import sys
from typing import Any, Dict, Generator, TypeVar

import pytest
from flask import Flask, url_for
from flask.testing import FlaskClient, FlaskCliRunner
from sqlalchemy.orm import scoped_session

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import application components
try:
    from app import create_app, db
    from app.auth.models import User
    from app.expenses.models import Category, Expense
    from app.restaurants.models import Restaurant
    from tests.test_config import TestConfig
except ImportError as e:
    print(f"Error importing modules: {e}")
    raise

# Type variable for generic type hints
T = TypeVar("T")


# Type for test client with auth support
class TestClient(FlaskClient):
    """Test client with authentication support."""

    def login(self, username: str, password: str, **kwargs) -> Any:
        """Log in a test user.

        Args:
            username: The username to log in with
            password: The password to use
            **kwargs: Additional arguments to pass to the request

        Returns:
            The response from the login request
        """
        from flask import url_for

        return self.post(
            url_for("auth.login"), data=dict(username=username, password=password), follow_redirects=True, **kwargs
        )

    def logout(self, **kwargs) -> Any:
        """Log out the current user.

        Args:
            **kwargs: Additional arguments to pass to the request

        Returns:
            The response from the logout request
        """
        from flask import url_for

        return self.get(url_for("auth.logout"), follow_redirects=True, **kwargs)


# Set environment variables for testing
os.environ["FLASK_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///:memory:?check_same_thread=False"

# Type variable for generic type hints
T = TypeVar("T")


@pytest.fixture(scope="session")
def app() -> Generator[Flask, None, None]:
    """Create and configure a Flask app for testing.

    This fixture is session-scoped to avoid recreating the app for each test.
    """
    # Create and configure the test app
    app = create_app(TestConfig)

    # Initialize the app with test config
    TestConfig.init_app(app)

    # Ensure the app is using the test client class
    app.test_client_class = TestClient

    # Push an application context for the duration of the tests
    ctx = app.app_context()
    ctx.push()

    yield app

    # Clean up after tests
    ctx.pop()


@pytest.fixture(scope="function")
def session(app: Flask) -> Generator[scoped_session, None, None]:
    """Create a new database session with a rollback at the end of the test."""
    with app.app_context():
        # Start a transaction
        connection = db.engine.connect()
        transaction = connection.begin()

        # Create a session bound to this connection
        session = db.create_scoped_session(
            {
                "bind": connection,
                "binds": {},
            }
        )

        # Override the default session with our scoped session
        db.session = session

        try:
            yield session

            # Rollback the transaction after the test
            transaction.rollback()
        finally:
            # Close the session and connection
            session.close()
            connection.close()


@pytest.fixture(scope="function")
def client(app: Flask, session: scoped_session) -> Generator[TestClient, None, None]:
    """A test client for the app with automatic cleanup.

    Args:
        app: The Flask application
        session: Database session fixture

    Yields:
        TestClient: Configured test client
    """
    with app.test_client() as test_client:
        with app.app_context():
            yield test_client
            # Clean up any pending database operations
            session.rollback()


@pytest.fixture(scope="function")
def runner(app: Flask) -> FlaskCliRunner:
    """A test runner for the app's CLI commands."""
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def test_user(session: scoped_session) -> Dict[str, Any]:
    """Create a test user and return user data.

    Args:
        session: Database session

    Returns:
        Dict containing test user data
    """
    user = User(username="testuser", email="test@example.com")
    user.set_password("testpass")
    session.add(user)
    session.commit()
    return {"id": user.id, "username": user.username, "email": user.email, "password": "testpass"}


@pytest.fixture(scope="function")
def auth_headers(client: FlaskClient, test_user: Dict[str, Any]) -> Dict[str, str]:
    """Get authentication headers for the test user.

    Args:
        client: Test client
        test_user: Test user data

    Returns:
        Dictionary with authentication headers
    """
    response = client.post(
        url_for("auth.login"),
        data={"username": test_user["username"], "password": test_user["password"]},
        follow_redirects=True,
    )
    assert response.status_code == 200, "Login failed"
    # Return the session cookie as the auth token
    return {"Cookie": response.headers.get("Set-Cookie", "")}


@pytest.fixture(scope="function")
def authenticated_client(client: FlaskClient, auth_headers: Dict[str, str]) -> FlaskClient:
    """A test client that is authenticated as the test user.

    Args:
        client: Test client
        auth_headers: Authentication headers

    Returns:
        Authenticated test client
    """
    client.environ_base["HTTP_AUTHORIZATION"] = auth_headers.get("Authorization")
    if "Cookie" in auth_headers:
        client.set_cookie("localhost", "session", auth_headers["Cookie"])
    return client


@pytest.fixture(scope="function")
def _db(app: Flask) -> Generator[scoped_session, None, None]:
    """Create a database for the tests.

    Args:
        app: The Flask application.

    Yields:
        SQLAlchemy: The database instance.
    """
    # The app fixture already handles database setup and teardown
    with app.app_context():
        # Ensure we have a clean database state
        db.session.commit()

        # Yield the database instance
        yield db

        # Rollback any uncommitted changes
        db.session.rollback()


# Clean up any remaining test data
@pytest.fixture(autouse=True)
def cleanup_test_data(session: scoped_session) -> None:
    """Clean up any test data after each test.

    This runs automatically after each test to ensure a clean state.
    """
    yield
    session.rollback()
    session.remove()


class AuthActions:
    """Helper class for authentication actions in tests."""

    def __init__(self, client: FlaskClient) -> None:
        """Initialize with a test client.

        Args:
            client: The test client.
        """
        self._client = client

    def login(self, username: str = "testuser", password: str = "testpass") -> Any:
        """Log in a test user.

        Args:
            username: The username to log in with.
            password: The password to log in with.

        Returns:
            The response from the login request.
        """
        from flask import url_for

        return self._client.post(
            url_for("auth.login"), data={"username": username, "password": password}, follow_redirects=True
        )

    def logout(self, **kwargs) -> Any:
        """Log out the test user."""
        from flask import url_for

        return self._client.get(url_for("auth.logout"), follow_redirects=True, **kwargs)

    def create_user(self, username: str = "testuser", password: str = "testpass") -> Any:
        """Create a test user.

        Args:
            username: The username to create.
            password: The password to use.

        Returns:
            The response from the user creation request.
        """
        from flask import url_for

        return self._client.post(
            url_for("auth.register"),
            data={"username": username, "password": password, "confirm_password": password},
            follow_redirects=True,
        )


@pytest.fixture
def auth(client: FlaskClient) -> AuthActions:
    """Create an AuthActions instance for the test client.

    Args:
        client: The test client.

    Returns:
        AuthActions: An instance of AuthActions for the test client.
    """
    return AuthActions(client)


@pytest.fixture(scope="function")
def test_restaurant(session: scoped_session, test_user: Dict[str, Any]) -> Restaurant:
    """Create a test restaurant.

    Args:
        session: Database session
        test_user: Test user data

    Returns:
        Restaurant: The created test restaurant
    """
    restaurant = Restaurant(name="Test Restaurant", address="123 Test St", created_by=test_user["id"])
    session.add(restaurant)
    session.commit()
    return restaurant


@pytest.fixture(scope="function")
def test_expense(session: scoped_session, test_user: Dict[str, Any], test_restaurant: Restaurant) -> Expense:
    """Create a test expense.

    Args:
        session: Database session
        test_user: Test user data
        test_restaurant: Test restaurant data

    Returns:
        Expense: The created test expense
    """
    # Create a category if it doesn't exist
    category = session.query(Category).filter_by(name="Test Category").first()
    if not category:
        category = Category(name="Test Category", created_by=test_user["id"])
        session.add(category)
        session.commit()

    expense = Expense(
        amount=25.50,
        date="2023-01-01",
        description="Test expense",
        restaurant_id=test_restaurant.id,
        category_id=category.id,
        created_by=test_user["id"],
    )
    session.add(expense)
    session.commit()
    return expense
