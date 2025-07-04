#!/usr/bin/env python3
"""Verify the persistent database connection and data persistence."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def verify_persistent_db():
    """Verify the persistent database connection and data persistence."""
    try:
        # Set environment variables for persistent database
        db_path = Path.home() / ".meal_expense_tracker" / "meal_expenses.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["FLASK_APP"] = "app"
        os.environ["FLASK_ENV"] = "development"

        print(f"Using database: {db_path}")
        print(f"Database exists: {db_path.exists()}")

        # Import after setting environment variables
        from app import create_app, db
        from sqlalchemy import inspect, text

        # Create app
        app = create_app()

        with app.app_context():
            # Test connection
            print("\nTesting database connection...")
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print(f"✓ Connection test: {result.scalar() == 1}")

            # Get database info
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            print("\nTables in database:")
            for table in tables:
                print(f"- {table}")

            # Test data persistence
            print("\nTesting data persistence...")
            from app.auth.models import User
            from sqlalchemy.exc import IntegrityError

            try:
                # Try to create a test user
                test_user = User(username="test_user")
                test_user.set_password("test_password")
                db.session.add(test_user)
                db.session.commit()
                print("✓ Successfully created test user")

                # Verify the user was saved
                user_count = db.session.query(User).count()
                print(f"✓ Total users in database: {user_count}")

                # Clean up
                db.session.delete(test_user)
                db.session.commit()

            except IntegrityError:
                print("ℹ️ Test user already exists")

            print("\n✓ Database verification complete!")
            return 0

    except Exception as e:
        print(f"Error verifying database: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(verify_persistent_db())
