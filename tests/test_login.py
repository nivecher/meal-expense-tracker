"""Test script for login functionality."""

import os
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
sys.path.insert(0, project_root)

from app import create_app, db  # noqa: E402
from app.auth.models import User  # noqa: E402


def test_login():
    # Create app context with test configuration
    app = create_app("testing")

    with app.app_context():
        # Create all database tables
        db.create_all()

        # Create a test user if it doesn't exist
        user = User.query.filter_by(username="nivecher").first()
        if not user:
            user = User(username="nivecher")
            user.set_password("nivecher")  # Set the password
            db.session.add(user)
            db.session.commit()

        print(f"User found/created: {user.username}")
        print(f"Password hash: {user.password_hash}")

        # Test password verification
        test_passwords = ["nivecher", "wrongpassword"]
        for pwd in test_passwords:
            result = user.check_password(pwd)
            print(f"Checking password '{pwd}': {'CORRECT' if result else 'INCORRECT'}")
            if result:
                print(f"  - Login successful with password: {pwd}")
            else:
                print(f"  - Login failed with password: {pwd}")


if __name__ == "__main__":
    test_login()
