"""Script to create a test user for Google Places sync testing."""

import os
from dotenv import load_dotenv
from app import create_app, db
from app.auth.models import User


def create_test_user():
    """Create a test user if it doesn't exist."""
    app = create_app()
    with app.app_context():
        # Check if test user already exists
        test_username = os.getenv("TEST_USERNAME", "testuser")
        test_password = os.getenv("TEST_PASSWORD", "testpassword123")

        user = User.query.filter_by(username=test_username).first()
        if not user:
            print(f"Creating test user: {test_username}")
            user = User(username=test_username)
            user.set_password(test_password)
            db.session.add(user)
            db.session.commit()
            print("Test user created successfully!")
        else:
            print(f"Test user {test_username} already exists.")

        print(f"Test user credentials:")
        print(f"Username: {test_username}")
        print(f"Password: {test_password}")


if __name__ == "__main__":
    load_dotenv()
    create_test_user()
