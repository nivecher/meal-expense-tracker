#!/usr/bin/env python3
"""Test Flask database configuration."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_flask_db():
    """Test Flask database configuration."""
    try:
        # Set environment variables
        os.environ["FLASK_APP"] = "app"
        os.environ["FLASK_ENV"] = "development"

        # Import Flask and create app
        from app import create_app, db
        from flask_migrate import Migrate

        # Create app
        app = create_app()
        migrate = Migrate(app, db)

        # Print database URI
        print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

        # Create tables
        with app.app_context():
            # Drop all tables
            db.drop_all()

            # Create all tables
            db.create_all()

            # Check if tables were created
            from sqlalchemy import inspect

            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print("\nTables in database:")
            for table in tables:
                print(f"- {table}")

            # Create a migration
            print("\nCreating migration...")
            from flask_migrate import migrate as migrate_command

            migrate_command(message="Initial migration")

            print("\nMigration created successfully!")

        return 0

    except Exception as e:
        print(f"Error testing Flask database: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(test_flask_db())
