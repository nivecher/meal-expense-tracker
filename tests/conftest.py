import os
import uuid
from datetime import datetime
from typing import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from app import create_app, db
from app.auth.models import User
from app.expenses.models import Category, Expense
from app.restaurants.models import Restaurant
from config import TestingConfig

# Set test environment variables
os.environ["FLASK_ENV"] = "testing"
os.environ["FLASK_APP"] = "app"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///:memory:?check_same_thread=False"


@pytest.fixture(scope="session")
def app() -> Generator[Flask, None, None]:
    """Create and configure a new app instance for testing."""
    # Create app with testing config
    app = create_app(TestingConfig)
    app.testing = True

    # Configure test settings
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing
    app.config["WTF_CSRF_CHECK_DEFAULT"] = False

    # Create a test client that handles CSRF tokens properly
    class TestClient(FlaskClient):
        def open(self, *args, **kwargs):
            # Add CSRF token to form data for POST requests
            if kwargs.get('method') in ('POST', 'PUT', 'PATCH', 'DELETE'):
                if 'data' in kwargs and isinstance(kwargs['data'], dict):
                    kwargs['data']['csrf_token'] = 'dummy_csrf_token'
            return super().open(*args, **kwargs)
    
    # Add CSRF token to template context
    @app.context_processor
    def inject_csrf_token():
        return {'csrf_token': lambda: 'dummy_csrf_token'}

    app.test_client_class = TestClient

    with app.app_context():
        db.create_all()
        # Initialize default categories if needed
        if not Category.query.first():
            db.session.add_all(
                [
                    Category(name="Dining", description="Expenses at restaurants, cafes, etc.", color="#FF6347"),
                    Category(name="Groceries", description="Food purchased from grocery stores", color="#4682B4"),
                    Category(name="Transport", description="Travel expenses related to meals", color="#32CD32"),
                    Category(name="Other", description="Miscellaneous meal-related expenses", color="#808080"),
                ]
            )
            db.session.commit()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app: Flask) -> Generator[FlaskClient, None, None]:
    """A test client for the app with request context."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def runner(app: Flask) -> FlaskCliRunner:
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def session(app: Flask) -> Generator[Session, None, None]:
    """Create a new database session for testing with proper isolation."""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        session_factory = sessionmaker(bind=connection, expire_on_commit=False)
        session = scoped_session(session_factory)

        old_session = db.session
        db.session = session

        yield session

        session.remove()
        transaction.rollback()
        connection.close()
        db.session = old_session


@pytest.fixture
def auth(client):
    """Return an object with authentication methods for testing."""

    class AuthActions:
        def __init__(self, client):
            self._client = client

        def login(self, username, password):
            # For testing, we'll set up the session directly instead of going through the login route
            from app.auth.models import User

            # Get the user by username
            user = User.query.filter_by(username=username).first()
            if not user or not user.check_password(password):
                raise ValueError(f"Invalid username or password for test user: {username}")

            # Set up the session directly
            with self._client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
                sess["_fresh"] = True  # Mark session as fresh
                sess["_id"] = "test-session-id"

            return self._client

        def logout(self):
            # Clear the session
            with self._client.session_transaction() as sess:
                sess.clear()
            return self._client

    return AuthActions(client)


@pytest.fixture
def test_user(session: Session) -> User:
    """Create and return a test user with known credentials."""
    from app.auth.models import User

    username = "testuser_1"
    password = "testpass"  # noqa: S105

    # Check if user already exists
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
        user.set_password(password)
        session.add(user)
        session.commit()  # Ensure the user is committed to the database
        session.refresh(user)
    return user


@pytest.fixture
def test_restaurant(session: Session, test_user: User) -> Restaurant:
    """Create and return a test restaurant."""
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
    )
    session.add(restaurant)
    session.commit()
    session.refresh(restaurant)
    return restaurant


@pytest.fixture
def test_expense(session: Session, test_user: User, test_restaurant: Restaurant) -> Expense:
    """Create a test expense."""
    expense = Expense(
        amount=10.99,
        date=datetime.utcnow().date(),
        notes="Test expense",
        user_id=test_user.id,
        restaurant_id=test_restaurant.id,
        meal_type="Lunch",
        category_id=Category.query.filter_by(name="Dining").first().id,  # Assuming 'Dining' category exists
    )
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


@pytest.fixture(autouse=True, scope="function")
def clean_database(app):
    """Clean the database before each test function."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        # Optionally, re-initialize default categories if needed
        if not Category.query.first():
            db.session.add_all(
                [
                    Category(name="Dining", description="Expenses at restaurants, cafes, etc.", color="#FF6347"),
                    Category(name="Groceries", description="Food purchased from grocery stores", color="#4682B4"),
                    Category(name="Transport", description="Travel expenses related to meals", color="#32CD32"),
                    Category(name="Other", description="Miscellaneous meal-related expenses", color="#808080"),
                ]
            )
            db.session.commit()
        yield
