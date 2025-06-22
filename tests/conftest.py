"""Pytest configuration and fixtures for the application."""

import os
import sys
from typing import Generator, Dict, Any

import pytest
from flask import Flask, url_for
from flask.testing import FlaskClient, FlaskCliRunner
from sqlalchemy.orm import Session

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402
from tests.test_config import TestConfig, TestClient  # noqa: E402
from app.expenses.category import Category  # noqa: F401

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
def client(app: Flask) -> Generator[TestClient, None, None]:
    """A test client for the app with automatic cleanup."""
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def runner(app: Flask) -> FlaskCliRunner:
    """A test runner for the app's CLI commands."""
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def session(app: Flask) -> Generator[Session, None, None]:
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
def auth_client(client: TestClient) -> TestClient:
    """A test client with authentication helpers."""
    return client


@pytest.fixture(scope="function")
def test_user(app: Flask, session: Session) -> Dict[str, Any]:
    """Create a test user and return user data."""
    from app.auth.models import User

    user = User(username="testuser", email="test@example.com")
    user.set_password("testpassword")

    session.add(user)
    session.commit()

    return {"id": user.id, "username": user.username, "email": user.email, "password": "testpassword"}


@pytest.fixture(scope="function")
def auth_headers(auth_client: TestClient, test_user: Dict[str, Any]) -> Dict[str, str]:
    """Get authentication headers for the test user."""
    # Login to get the auth token
    response = auth_client.post(
        url_for("auth.login"),
        data={"username": test_user["username"], "password": test_user["password"]},
        follow_redirects=True,
    )

    # Get the session cookie
    session_cookie = auth_client.cookie_jar._cookies.get("localhost.local").get("session")

    # Return headers with the session cookie
    return {"Cookie": f"session={session_cookie.value}"}


@pytest.fixture(scope="function")
def authenticated_client(auth_client: TestClient, auth_headers: Dict[str, str]) -> TestClient:
    """A test client that is authenticated as the test user."""
    # Set the auth headers for subsequent requests
    for key, value in auth_headers.items():
        auth_client.environ_base[key] = value

    return auth_client


@pytest.fixture(scope="function")
def _db(app: Flask) -> Generator[Any, None, None]:
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


@pytest.fixture(scope="function")
def client(app: Flask, _db: Any) -> Generator[FlaskClient, None, None]:
    """A test client for the app with a clean database for each test.

    Args:
        app: The Flask application.
        _db: The database fixture.

    Yields:
        FlaskClient: The test client.
    """
    # The _db fixture already handles table creation and cleanup
    with app.app_context():
        # Create a test client
        with app.test_client() as client:
            yield client

        # Ensure the session is cleaned up
        db.session.remove()


@pytest.fixture(scope="function")
def runner(app: Flask, _db: Any) -> Any:
    """A test CLI runner for the app.

    Args:
        app: The Flask application.
        _db: The database fixture.

    Yields:
        FlaskCliRunner: The test CLI runner.
    """
    with app.test_cli_runner() as runner:
        yield runner


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
        return self._client.post(
            "/auth/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    def logout(self):
        """Log out the test user."""
        return self._client.get("/auth/logout", follow_redirects=True)

    def create_user(self, username="testuser", password="testpass"):
        """Create a test user."""
        return self._client.post(
            "/auth/register",
            data={"username": username, "password": password},
            follow_redirects=True,
        )


@pytest.fixture(scope="function")
def auth(client: FlaskClient) -> "AuthActions":
    """Create an AuthActions object for testing authentication.

    Args:
        client: The test client.

    Returns:
        AuthActions: An instance of AuthActions for the test client.
    """
    return AuthActions(client)


@pytest.fixture(scope="function")
def test_user(app: Flask, _db: Any, auth: "AuthActions") -> User:
    """Create a test user.

    Args:
        app: The Flask application.
        _db: The database fixture.
        auth: The auth fixture.

    Returns:
        User: The created test user.
    """
    # Check if user already exists
    user = User.query.filter_by(username="testuser").first()
    if user is None:
        user = User(
            username="testuser",
            email="test@example.com",
            password=User.generate_password("testpass"),  # Use password setter
            is_active=True,
        )
        db.session.add(user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating test user: {e}")
            raise
    return user


@pytest.fixture(scope="function")
def test_restaurant(app: Flask, _db: Any, test_user: User) -> Restaurant:
    """Create a test restaurant.

    Args:
        app: The Flask application.
        _db: The database fixture.
        test_user: The test user who owns the restaurant.

    Returns:
        Restaurant: The created test restaurant.
    """
    # Check if restaurant already exists
    restaurant = Restaurant.query.filter_by(name="Test Restaurant").first()
    if restaurant is None:
        restaurant = Restaurant(
            name="Test Restaurant",
            address="123 Test St",
            city="Test City",
            state="TS",
            postal_code="12345",
            country="Test Country",
            phone="123-456-7890",
            website="https://testrestaurant.example.com",
            user_id=test_user.id,
            is_active=True,
        )
        db.session.add(restaurant)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating test restaurant: {e}")
            raise
    _db.session.commit()

    return restaurant


@pytest.fixture(scope="function")
def test_expense(app: Flask, _db: Any, test_user: User, test_restaurant: Restaurant) -> Expense:
    """Create a test expense.

    Args:
        app: The Flask application.
        _db: The database fixture.
        test_user: The test user who made the expense.
        test_restaurant: The restaurant where the expense was made.

    Returns:
        Expense: The created test expense.
    """
    from datetime import datetime, timezone

    # Get or create a default category

    category = Category.query.filter_by(name="Dining").first()
    if category is None:
        category = Category(name="Dining", description="Dining out expenses")
        db.session.add(category)
        db.session.commit()

    # Create the expense
    expense = Expense(
        amount=25.50,
        notes="Test expense",
        date=datetime.now(timezone.utc),
        meal_type="lunch",
        user_id=test_user.id,
        restaurant_id=test_restaurant.id,
        category_id=category.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.session.add(expense)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating test expense: {e}")
        raise

    return expense
