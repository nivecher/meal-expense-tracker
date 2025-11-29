"""Script to create an admin user."""

from app import create_app
from app.auth.models import User
from app.extensions import db


def create_admin_user(username: str, email: str, password: str) -> None:
    """Create an admin user.

    Args:
        username: The username for the admin
        email: The email for the admin
        password: The password for the admin
    """
    app = create_app()
    with app.app_context():
        # Check if user already exists
        if User.query.filter_by(username=username).first() is not None:
            print(f"User {username} already exists.")
            return

        # Create the admin user
        admin = User(username=username, email=email, is_admin=True, is_active=True)
        admin.set_password(password)

        # Add to database
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user {username} created successfully.")


if __name__ == "__main__":
    import getpass

    print("Create Admin User")
    print("================")
    username = input("Username: ")
    email = input("Email: ")
    password = getpass.getpass("Password: ")
    confirm_password = getpass.getpass("Confirm Password: ")

    if password != confirm_password:
        print("Error: Passwords do not match.")
    else:
        create_admin_user(username, email, password)
