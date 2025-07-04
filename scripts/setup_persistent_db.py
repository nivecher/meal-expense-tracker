#!/usr/bin/env python3
"""Set up a persistent SQLite database for the application."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def setup_persistent_db():
    """Set up a persistent SQLite database."""
    try:
        # Get the home directory
        home_dir = Path.home()
        db_dir = home_dir / ".meal_expense_tracker"
        db_path = db_dir / "meal_expenses.db"

        # Create the directory if it doesn't exist
        db_dir.mkdir(exist_ok=True, parents=True)

        # Set permissions (read/write for user only)
        db_dir.chmod(0o700)

        # Create the database file if it doesn't exist
        if not db_path.exists():
            db_path.touch()
            db_path.chmod(0o600)  # Read/write for user only
            print(f"Created new database file: {db_path}")

        # Set the database URI in environment
        db_uri = f"sqlite:///{db_path}"

        # Update environment variables
        os.environ["DATABASE_URL"] = db_uri
        os.environ["FLASK_APP"] = "wsgi:app"
        os.environ["FLASK_ENV"] = "development"

        print(f"Database URI set to: {db_uri}")
        print(f"Database file permissions: {oct(db_path.stat().st_mode)[-3:]}")

        # Test the connection
        from app import create_app, db

        app = create_app()

        with app.app_context():
            # Test the connection
            connection = db.engine.connect()
            print("\n✓ Successfully connected to the database")

            # Create all tables
            db.create_all()
            print("✓ Database tables created/verified")

            # List all tables
            from sqlalchemy import inspect

            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            print("\nTables in database:")
            for table in tables:
                print(f"- {table}")

            connection.close()

        print("\n✓ Persistent database setup complete!")
        print(f"Database file location: {db_path}")

        return 0

    except Exception as e:
        print(f"Error setting up persistent database: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(setup_persistent_db())
