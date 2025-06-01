from app.auth.models import User
from app import db
from sqlalchemy.exc import SQLAlchemyError


def test_register(client, app):
    """Test user registration."""
    # Test GET request first
    response = client.get("/auth/register")
    assert response.status_code == 200
    assert b"Register" in response.data

    # Test successful registration
    response = client.post(
        "/auth/register",
        data={"username": "testuser", "password": "testpass"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Registration successful! Please login." in response.data

    # Verify user was created in database
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        assert user is not None
        assert user.username == "testuser"
        assert user.check_password("testpass")


def test_register_missing_fields(client):
    """Test registration with missing fields."""
    response = client.post(
        "/auth/register",
        data={"username": "testuser"},  # Missing password
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Please fill out all fields." in response.data

    response = client.post(
        "/auth/register",
        data={"password": "testpass"},  # Missing username
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Please fill out all fields." in response.data


def test_register_existing_username(client, app):
    """Test registration with existing username."""
    # First register a user
    with app.app_context():
        user = User(username="testuser")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

    # Try to register the same username again
    response = client.post(
        "/auth/register",
        data={"username": "testuser", "password": "testpass"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Username already exists" in response.data
    assert b"Register" in response.data  # Should stay on register page


def test_register_authenticated_user(client, auth, app):
    """Test registration when user is already authenticated."""
    # Create and login a user first
    with app.app_context():
        user = User(username="testuser")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

    auth.login()
    response = client.get("/auth/register", follow_redirects=True)
    assert response.status_code == 200
    assert b"Meal Expenses" in response.data  # Should redirect to index


def test_login(client, app):
    """Test user login."""
    # First register a user
    with app.app_context():
        user = User(username="testuser")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

    # Try to login
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpass"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome back!" in response.data


def test_login_with_next(client, app):
    """Test login with next parameter."""
    # First register a user
    with app.app_context():
        user = User(username="testuser")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

    # Try to login with next parameter
    response = client.post(
        "/auth/login?next=/expenses/add",
        data={"username": "testuser", "password": "testpass"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Add Expense" in response.data  # Should redirect to add expense page


def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "wrongpass"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_login_authenticated_user(client, auth, app):
    """Test login when user is already authenticated."""
    # Create and login a user first
    with app.app_context():
        user = User(username="testuser")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

    auth.login()
    response = client.get("/auth/login", follow_redirects=True)
    assert response.status_code == 200
    assert b"Meal Expenses" in response.data  # Should redirect to index


def test_logout(client, auth):
    """Test user logout."""
    auth.login()
    response = client.get("/auth/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been logged out" in response.data


def test_logout_unauthenticated(client):
    """Test logout when user is not authenticated."""
    response = client.get("/auth/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been logged out" in response.data


def test_register_database_error(client, app, monkeypatch):
    """Test registration with database error."""

    def mock_commit_error():
        raise SQLAlchemyError("Database error")

    # First register a user
    with app.app_context():
        user = User(username="testuser")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

    # Mock the commit to raise an error
    monkeypatch.setattr(db.session, "commit", mock_commit_error)

    # Try to register
    response = client.post(
        "/auth/register",
        data={"username": "newuser", "password": "testpass"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Error creating user. Please try again." in response.data
