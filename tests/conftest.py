"""Pytest configuration and fixtures for the test suite."""

import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Generator, Optional, TypeVar

import pytest
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner
from sqlalchemy.orm import Session, scoped_session, sessionmaker

# Add the project root to the Python path first to avoid import issues
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Import application components with proper error handling
try:
    from app import create_app  # noqa: E402
    from app.auth.models import User  # noqa: E402
    from app.expenses.models import Category, Expense  # noqa: E402
    from app.extensions import db  # noqa: E402
    from app.restaurants.models import Restaurant  # noqa: E402
except ImportError as e:
    print(f"Error importing application modules: {e}")
    raise

# Type variable for generic test fixtures
T = TypeVar("T")

# Set test environment variables
os.environ.update(
    {
        "FLASK_ENV": "testing",
        "FLASK_APP": "app",
        "FLASK_CONFIG": "testing",
        "SECRET_KEY": "test-secret-key",
        "DATABASE_URL": "sqlite:///:memory:",
        "TESTING": "True",
        "WTF_CSRF_ENABLED": "False",
    }
)


@pytest.fixture(scope="function")
def app() -> Generator[Flask, None, None]:
    """Create and configure a new app instance for testing.

    This fixture is function-scoped to ensure a clean database for each test.
    """
    # Create app with testing config
    app = create_app("testing")

    # Configure the test app with in-memory SQLite
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY="test-secret-key",
        SERVER_NAME="localhost",
        PREFERRED_URL_SCHEME="http",
        APPLICATION_ROOT="/",
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "connect_args": {"check_same_thread": False},
            "poolclass": None,  # Use NullPool for SQLite in-memory
        },
    )

    # Initialize template filters
    from app.template_filters import init_app as init_filters
    from app.utils.filters import init_app as init_utils_filters

    init_filters(app)
    init_utils_filters(app)

    # Set up test client class with CSRF handling
    class TestClient(FlaskClient):
        def open(self, *args, **kwargs):
            # Add CSRF token to all requests
            if kwargs.get("method") in ("POST", "PUT", "PATCH", "DELETE"):
                if "data" in kwargs:
                    if isinstance(kwargs["data"], dict):
                        kwargs["data"] = {**kwargs["data"], "csrf_token": "dummy_csrf_token"}
                    elif isinstance(kwargs["data"], str):
                        kwargs["data"] = f"{kwargs['data']}&csrf_token=dummy_csrf_token"
            return super().open(*args, **kwargs)

    app.test_client_class = TestClient

    # Push application context
    ctx = app.app_context()
    ctx.push()

    # Create database schema and initialize app
    from app.database import init_database

    # Initialize the database
    init_database(app)

    # Create all tables
    db.create_all()

    yield app

    # Clean up after tests
    db.session.remove()
    db.drop_all()
    db.session.remove()

    # Pop the application context
    ctx.pop()


# Type stubs are not needed as we're importing the actual models
# at the top of the file


@pytest.fixture
def client(app: Flask) -> Generator[FlaskClient, None, None]:
    """Create a test client for the application with database access.

    This fixture provides a test client that can be used to make requests
    to the application for testing purposes, with proper database session handling.
    """
    with app.test_client() as client:
        with app.app_context():
            # Create all tables if they don't exist
            db.create_all()

            # Start a new transaction
            connection = db.engine.connect()
            transaction = connection.begin()

            # Create a new scoped session for the test
            db.session = db.create_scoped_session(options={"bind": connection, "binds": {}})

            # Bind the session to the current app context
            db.session.begin_nested()

            try:
                yield client
            finally:
                # Clean up the session and transaction
                db.session.rollback()
                db.session.close()
                transaction.rollback()
                connection.close()
                db.session.remove()


@pytest.fixture
def runner(app: Flask) -> FlaskCliRunner:
    """Create a CLI runner for testing Click commands.

    Args:
        app: The Flask application fixture.

    Returns:
        FlaskCliRunner: The CLI test runner.
    """
    return app.test_cli_runner()


@pytest.fixture
def _db(app: Flask) -> Generator[scoped_session, None, None]:
    """Provide a transactional scope around tests.

    This fixture is used by Flask-SQLAlchemy to ensure each test runs in a transaction
    that's rolled back at the end of the test.
    """
    # Create all tables if they don't exist
    with app.app_context():
        db.create_all()

    # Create a new connection and transaction
    connection = db.engine.connect()
    transaction = connection.begin()

    # Create a scoped session bound to the transaction
    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)

    # Override the default session with our scoped session
    db.session = session

    try:
        yield session
    finally:
        # Clean up the session and transaction
        session.rollback()
        session.close()
        transaction.rollback()
        connection.close()
        session.remove()

        # Reset the session
        db.session = db.create_scoped_session()


@pytest.fixture
def session(_db: scoped_session) -> Session:
    """Create a new database session for testing.

    This fixture provides a session that's bound to the current test's transaction.
    All database operations will be rolled back after the test completes.
    """
    return _db()


class AuthActions:
    """Helper class for authentication-related test actions."""

    def __init__(self, client: FlaskClient) -> None:
        """Initialize with the test client.

        Args:
            client: The Flask test client.
        """
        self._client = client
        self._app: Optional[Flask] = None

    def _get_app(self) -> Flask:
        """Get the Flask application instance.

        Returns:
            The Flask application instance.
        """
        if self._app is None:
            from flask import current_app as flask_current_app

            self._app = flask_current_app._get_current_object()  # type: ignore
        return self._app

    def login(self, username: str, password: str) -> FlaskClient:
        """Log in a user for testing.

        Args:
            username: The username to log in with.
            password: The password to authenticate with.

        Returns:
            The test client with an authenticated session.

        Raises:
            ValueError: If the username or password is invalid.
        """
        from app.auth.models import User

        with self._get_app().app_context():
            user = User.query.filter_by(username=username).first()
            if not user or not user.check_password(password):
                raise ValueError(f"Invalid username or password for test user: {username}")

            # Use session_transaction in a way that doesn't expect a return value
            with self._client.session_transaction() as sess:  # type: ignore[func-returns-value]
                sess["_user_id"] = str(user.id)
                sess["_fresh"] = True  # Mark session as fresh
                sess["_id"] = "test-session-id"
            # Force the session to be saved
            self._client.get("/")

        return self._client

    def logout(self) -> FlaskClient:
        """Log out the current user.

        Returns:
            The test client with cleared session.
        """
        # Clear the session
        with self._client.session_transaction() as sess:  # type: ignore[func-returns-value]
            sess.clear()
        # Force the session to be saved
        self._client.get("/")
        return self._client

    def register(self, username: str, password: str, email: Optional[str] = None) -> "User":
        """Register and log in a new test user.

        Args:
            username: The username for the new user.
            password: The password for the new user.
            email: Optional email for the new user. Defaults to username@example.com.

        Returns:
            The created User instance.
        """
        from app.auth.models import User

        if email is None:
            email = f"{username}@example.com"

        user = User(username=username, email=email)
        user.set_password(password)

        with self._get_app().app_context():
            db.session.add(user)
            db.session.commit()

        return user

    def create_user(self, username: str, password: str, email: str = "test@example.com") -> "User":
        """Create a user directly in the database.

        Args:
            username: The username for the new user.
            password: The password for the new user.
            email: The email for the new user. Defaults to test@example.com.

        Returns:
            The created User instance.
        """
        from app.auth.models import User

        user = User(username=username, email=email)
        user.set_password(password)

        with self._get_app().app_context():
            db.session.add(user)
            db.session.commit()
        return user


@pytest.fixture
def auth(client: FlaskClient) -> AuthActions:
    """Return an object with authentication methods for testing.

    Args:
        client: The test client fixture.

    Returns:
        AuthActions: An instance with authentication helper methods.
    """
    return AuthActions(client)


@pytest.fixture
def test_user(session: Session) -> User:
    """Create and return a test user with known credentials.

    Args:
        session: The database session fixture.

    Returns:
        User: A test user instance.
    """
    from app.auth.models import User

    username = "testuser_1"
    password = "testpass"  # noqa: S105
    email = f"{username}@example.com"

    # Delete any existing test user to avoid conflicts
    session.query(User).filter(User.username == username).delete(synchronize_session=False)
    session.commit()

    # Create a new test user
    user = User(username=username, email=email)
    user.set_password(password)  # noqa: S106

    session.add(user)
    session.commit()
    session.refresh(user)

    # Verify the user was created correctly
    assert user.id is not None
    assert user.check_password(password)

    return user


@pytest.fixture
def test_user2(session: Session) -> User:
    """Create and return a second test user for testing access control.

    Args:
        session: The database session fixture.

    Returns:
        User: A second test user instance.
    """
    from app.auth.models import User

    username = "testuser_2"
    password = "testpass2"  # Different password than testuser_1
    email = f"{username}@example.com"

    # Delete any existing test user to avoid conflicts
    session.query(User).filter(User.username == username).delete(synchronize_session=False)
    session.commit()

    # Create a new test user
    user = User(username=username, email=email)
    user.set_password(password)

    session.add(user)
    session.commit()
    session.refresh(user)

    # Verify the user was created correctly
    assert user.id is not None
    assert user.check_password(password)

    return user


@pytest.fixture
def test_restaurant(session: Session, test_user: User) -> Restaurant:
    """Create and return a test restaurant.

    Args:
        session: The database session fixture.
        test_user: The test user who owns the restaurant.

    Returns:
        Restaurant: A test restaurant instance.
    """
    from app.restaurants.models import Restaurant

    # Ensure the test user is properly committed
    session.add(test_user)
    session.commit()
    session.refresh(test_user)

    # Create the restaurant with all required fields
    restaurant = Restaurant(
        name=f"Test Restaurant {uuid.uuid4().hex[:8]}",
        address="123 Test St",
        city="Test City",
        state="TS",
        postal_code="12345",
        phone="123-456-7890",
        website="https://example.com",
        notes="Test notes",
        user_id=test_user.id,
        type="restaurant",
        cuisine="Test Cuisine",
        price_range="$$",
        email=f"contact@testrestaurant{uuid.uuid4().hex[:4]}.com",
        country="United States",
    )

    # Add and commit the restaurant
    session.add(restaurant)
    session.commit()
    session.refresh(restaurant)

    # Ensure the relationship is properly set up
    if restaurant not in test_user.restaurants:
        test_user.restaurants.append(restaurant)
        session.commit()
        session.refresh(restaurant)
        session.refresh(test_user)

    return restaurant


@pytest.fixture
def test_category(session: Session, test_user: User) -> Category:
    """Create and return a test category.

    Args:
        session: The database session fixture.
        test_user: The test user who owns the category.

    Returns:
        Category: A test category instance.
    """
    from app.expenses.models import Category

    # Check if category already exists
    category = session.query(Category).filter_by(name="Test Category", user_id=test_user.id).first()

    if not category:
        category = Category(
            name="Test Category",
            user_id=test_user.id,
            description="Test category for expenses",
            color="#FF0000",
            is_default=False,
        )
        session.add(category)
        session.commit()
        session.refresh(category)

    return category


@pytest.fixture
def test_expense(session: Session, test_user: User, test_restaurant: Restaurant, test_category: Category) -> Expense:
    """Create a test expense.

    Args:
        session: The database session fixture.
        test_user: The test user who owns the expense.
        test_restaurant: The restaurant associated with the expense.
        test_category: The category for the expense.

    Returns:
        Expense: A test expense instance.
    """
    from app.expenses.models import Expense

    # Create the expense with Decimal amount and timezone-aware datetime
    expense = Expense(
        amount=Decimal("10.99"),
        date=datetime.now(timezone.utc),
        notes="Test expense",
        user_id=test_user.id,
        restaurant_id=test_restaurant.id,
        meal_type="Lunch",
        category_id=test_category.id,
    )
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


# Remove the clean_database fixture as it's causing issues with the transaction-based testing
