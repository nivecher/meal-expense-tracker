"""Script to ensure test user exists with correct password for Playwright tests."""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.auth.models import User
from app.extensions import db


def setup_test_user(username: str = "testuser_1", password: str = "testpass", email: str | None = None) -> None:
    """Ensure test user exists with correct password.

    Args:
        username: The username for the test user (default: testuser_1)
        password: The password for the test user (default: testpass)
        email: The email for the test user (default: {username}@example.com)
    """
    if email is None:
        email = f"{username}@example.com"

    app = create_app()
    with app.app_context():
        # Check if user already exists
        user = User.query.filter_by(username=username).first()

        if user is not None:
            # User exists - verify and update password if needed
            if user.check_password(password):
                print(f"✓ Test user '{username}' already exists with correct password.")
                return

            # Password doesn't match - update it
            print(f"⚠ Test user '{username}' exists but password is incorrect. Updating password...")
            user.set_password(password)
            # Ensure user is active
            user.is_active = True
            db.session.commit()
            print(f"✓ Updated password for test user '{username}'.")
        else:
            # User doesn't exist - create it
            print(f"Creating test user '{username}'...")
            user = User(username=username, email=email, is_active=True, is_admin=False)
            user.set_password(password)

            db.session.add(user)
            db.session.commit()
            print(f"✓ Test user '{username}' created successfully.")

        # Verify the user was set up correctly
        db.session.refresh(user)
        if user.check_password(password):
            print(f"✓ Verification: Test user '{username}' password is correct.")
        else:
            print(f"✗ Error: Password verification failed for '{username}'.")
            raise RuntimeError("Failed to set up test user password correctly.")


if __name__ == "__main__":
    import sys

    # Allow overriding defaults via command line
    username = sys.argv[1] if len(sys.argv) > 1 else "testuser_1"
    password = sys.argv[2] if len(sys.argv) > 2 else "testpass"

    setup_test_user(username=username, password=password)
    print("\nTest user is ready for Playwright tests!")
