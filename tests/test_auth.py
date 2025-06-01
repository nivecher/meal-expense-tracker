from app.auth.models import User
from app import create_app, db
from config import config


def test_register(client):
    """Test user registration."""
    response = client.post(
        "/auth/register",
        data={"username": "testuser", "password": "testpass"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Registration successful! Please login." in response.data

    with create_app(config["testing"]).app_context():
        user = User.query.filter_by(username="testuser").first()
        assert user is not None
        assert user.username == "testuser"


def test_register_existing_username(client):
    """Test registration with existing username."""
    # First register a user
    with create_app(config["testing"]).app_context():
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


def test_login(client):
    """Test user login."""
    # First register a user
    with create_app(config["testing"]).app_context():
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


def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "wrongpass"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_logout(client, auth):
    """Test user logout."""
    auth.login()
    response = client.get("/auth/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been logged out" in response.data
