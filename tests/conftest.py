import pytest
from app import create_app, db
from app.auth.models import User
from app.restaurants.models import Restaurant
from app.expenses.models import Expense
from config import config
from sqlalchemy.exc import SQLAlchemyError


@pytest.fixture(scope="session")
def app():
    """Create and configure a Flask app for testing."""
    app = create_app(config["testing"])
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="function")
def _db(app):
    """Create a fresh database for each test."""
    with app.app_context():
        db.drop_all()  # Ensure clean state
        db.create_all()
        yield db
        db.session.remove()
        db.session.close()
        db.drop_all()


@pytest.fixture(scope="function")
def client(app, _db):
    """A test client for the app."""
    with app.test_client() as client:
        with app.app_context():
            # Create test user
            user = User(username="testuser")
            user.set_password("testpass")
            db.session.add(user)
            db.session.commit()
        yield client


@pytest.fixture(scope="function")
def runner(app, _db):
    """A test CLI runner for the app."""
    with app.test_cli_runner() as runner:
        yield runner


class AuthActions:
    def __init__(self, client):
        self._client = client

    def login(self, username="testuser", password="testpass"):
        """Log in a test user."""
        return self._client.post(
            "/auth/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    def logout(self):
        """Log out the test user."""
        return self._client.get("/auth/logout", follow_redirects=True)


@pytest.fixture(scope="function")
def auth(client):
    """Create an AuthActions object for testing authentication."""
    return AuthActions(client)


@pytest.fixture(scope="function")
def test_user(app, _db):
    """Create a test user."""
    with app.app_context():
        try:
            user = User(username="testuser")
            user.set_password("testpass")
            db.session.add(user)
            db.session.commit()
            return user
        except SQLAlchemyError:
            db.session.rollback()
            raise


@pytest.fixture(scope="function")
def test_restaurant(app, _db, test_user):
    """Create a test restaurant."""
    with app.app_context():
        try:
            restaurant = Restaurant(
                name="Test Restaurant",
                city="Test City",
                address="123 Test St",
                phone="123-456-7890",
                website="http://test.com",
                type="restaurant",
                description="Test description",
                price_range="$$",
                cuisine="american",
                notes="Test notes",
            )
            db.session.add(restaurant)
            db.session.commit()
            return restaurant
        except SQLAlchemyError:
            db.session.rollback()
            raise


@pytest.fixture(scope="function")
def test_expense(app, _db, test_user, test_restaurant):
    """Create a test expense."""
    with app.app_context():
        try:
            expense = Expense(
                user=test_user,
                restaurant=test_restaurant,
                date="2024-02-20",
                meal_type="Lunch",
                category="Food",
                amount=25.50,
                notes="Test expense",
            )
            db.session.add(expense)
            db.session.commit()
            return expense
        except SQLAlchemyError:
            db.session.rollback()
            raise
