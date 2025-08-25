"""Test login flow functionality using pytest fixtures."""

from flask_login import login_user

from app.auth.models import User


def test_login_flow(app, session):
    """Test complete login flow with proper fixtures."""
    # Get or create test user
    username = "testuser"
    password = "testpassword123"

    # Delete existing test user if it exists
    existing_user = session.query(User).filter_by(username=username).first()
    if existing_user:
        session.delete(existing_user)
        session.commit()

    # Create new test user
    user = User(username=username, email=f"{username}@example.com")
    user.set_password(password)
    session.add(user)
    session.commit()

    # Test password verification
    assert user.check_password(password), "Password verification failed"

    # Test login with correct password
    with app.test_request_context():
        # Simulate login
        login_success = login_user(user)
        assert login_success, "Login failed"
