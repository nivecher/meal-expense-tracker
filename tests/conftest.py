"""Pytest configuration and fixtures for the application."""

import os
import uuid
from datetime import datetime
from typing import Any, Generator, Optional

import pytest
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from app import create_app, db
from app.auth.models import User
from app.expenses.models import Expense
from app.restaurants.models import Restaurant
from tests.test_config import TestConfig

# Set test environment variables
os.environ["FLASK_ENV"] = "testing"
os.environ["FLASK_APP"] = "app"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///:memory:?check_same_thread=False"


@pytest.fixture(scope="session")
def app() -> Generator[Flask, None, None]:
    """Create and configure a new app instance for testing."""
    # Create app with test config
    app = create_app(TestConfig)

    # Ensure app is in testing mode
    app.testing = True

    # Set up app context
    ctx = app.app_context()
    ctx.push()

    # Create all database tables
    db.create_all()

    yield app

    # Clean up
    db.session.remove()
    db.drop_all()
    ctx.pop()

    # Create the database and load test data
    with app.app_context():
        db.create_all()

    yield app

    # Clean up the temporary database
    with app.app_context():
        db.session.remove()
        db.drop_all()
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app: Flask) -> Generator[FlaskClient, None, None]:
    """A test client for the app with request context."""
    with app.test_client() as client:
        with app.app_context():
            # Set up test client headers
            client.environ_base["HTTP_HOST"] = "localhost:5000"
            client.environ_base["SERVER_NAME"] = "localhost"
            client.environ_base["SERVER_PORT"] = "5000"

            # Create all tables
            db.create_all()

            yield client

            # Clean up
            db.session.remove()
            db.drop_all()


@pytest.fixture
def runner(app: Flask) -> FlaskCliRunner:
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def session(app: Flask) -> Generator[Session, None, None]:
    """Create a new database session for testing with proper isolation."""
    # Create all tables
    with app.app_context():
        db.create_all()

        # Start a transaction
        connection = db.engine.connect()
        transaction = connection.begin()

        # Create a scoped session
        session_factory = sessionmaker(bind=connection, expire_on_commit=False)
        session = scoped_session(session_factory)

        # Store the original session and replace it with our scoped session
        old_session = db.session
        db.session = session

        yield session

        # Clean up
        session.remove()
        transaction.rollback()
        connection.close()
        db.session = old_session


class AuthActions:
    """Helper class for authentication in tests."""

    def __init__(self, client: FlaskClient) -> None:
        self._client = client
        self._user = None

    def login(self, username: str = "testuser", password: str = "testpass") -> Any:
        """Log in a test user and return the response."""
        return self._client.post(
            "/auth/login", data={"username": username, "password": password}, follow_redirects=True
        )

    def login_new_user(self, session: Session, username: str = None, password: str = "testpass") -> User:
        """Create a new user, log them in, and return the user object."""
        if username is None:
            username = f"testuser_{uuid.uuid4().hex[:8]}"

        # Create the user
        user = User(username=username)
        user.set_password(password)
        session.add(user)
        session.commit()
        session.refresh(user)

        # Log in the user
        self.login(username, password)
        self._user = user
        return user

    def logout(self) -> Any:
        """Log out the current user."""
        self._user = None
        return self._client.get("/auth/logout", follow_redirects=True)

    def register(self, username: str = None, password: str = "testpass") -> Any:
        """Register a new test user and return the response."""
        if username is None:
            username = f"testuser_{uuid.uuid4().hex[:8]}"

        return self._client.post(
            "/auth/register", data={"username": username, "password": password}, follow_redirects=True
        )

    def get_user(self) -> Optional[User]:
        """Get the currently logged-in user."""
        return self._user

    def create_user(self, username: str = None, password: str = "testpass") -> User:
        """Create a test user directly in the database.

        Args:
            username: Username for the test user
            password: Password for the test user

        Returns:
            User: The created user object
        """
        if username is None:
            username = f"testuser_{uuid.uuid4().hex[:8]}"

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def auth(client: FlaskClient) -> AuthActions:
    """Authentication test helper."""
    return AuthActions(client)


@pytest.fixture
def test_user(client: FlaskClient, auth: AuthActions) -> User:
    """Create and return a test user that's already logged in."""
    # Create and login a new user
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    password = "testpass"

    # Create user directly in the database
    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)

    # Log in the user
    auth.login(username, password)
    return user


@pytest.fixture
def test_restaurant(test_user: User, client: FlaskClient) -> Restaurant:
    """Create and return a test restaurant."""
    # Create a test restaurant
    restaurant = Restaurant(
        name=f"Test Restaurant {uuid.uuid4().hex[:8]}",
        address="123 Test St",
        city="Test City",
        state="TS",
        zip_code="12345",
        phone="123-456-7890",
        website="https://example.com",
        notes="Test notes",
        user_id=test_user.id,
        type="Restaurant",
        cuisine="Test Cuisine",
        price_range="$$",
    )
    db.session.add(restaurant)
    db.session.commit()
    db.session.refresh(restaurant)
    return restaurant


@pytest.fixture
def test_expense(session: Session, test_user: User, test_restaurant: Restaurant) -> Expense:
    """Create a test expense."""
    expense = Expense(
        amount=10.99,
        date=datetime.utcnow(),
        description="Test expense",
        user_id=test_user.id,
        restaurant_id=test_restaurant.id,
    )
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense
