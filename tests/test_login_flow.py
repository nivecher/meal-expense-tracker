import sys
from app import create_app, db
from app.auth.models import User


def test_login_flow():
    # Create app context
    app = create_app()

    with app.app_context():
        # Get or create test user
        username = "testuser"
        password = "testpassword123"

        # Delete existing test user if it exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()

        # Create new test user
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        print(f"Created test user: {username}")

        # Test password verification
        if user.check_password(password):
            print("✅ Password verification successful")
        else:
            print("❌ Password verification failed")
            return 1

        # Test login with correct password
        from flask_login import login_user

        with app.test_request_context():
            # Simulate login
            login_success = login_user(user)
            if login_success:
                print("✅ Login successful")
            else:
                print("❌ Login failed")
                return 1

        return 0


if __name__ == "__main__":
    sys.exit(test_login_flow())
