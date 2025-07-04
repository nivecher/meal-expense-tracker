#!/usr/bin/env python3
"""Verify database connection and list tables."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def verify_database_connection():
    """Verify the database connection and list tables."""
    try:
        # Set environment variables
        os.environ["FLASK_APP"] = "app"
        os.environ["FLASK_ENV"] = "development"

        # Import after setting environment variables
        from app import create_app, db
        from sqlalchemy import inspect

        # Create app
        app = create_app()

        with app.app_context():
            # Get database URI
            db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
            print(f"Database URI: {db_uri}")

            # Test connection
            print("\nTesting database connection...")
            connection = db.engine.connect()
            print("✓ Successfully connected to the database")

            # List all tables
            print("\nTables in database:")
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            if tables:
                for table in tables:
                    print(f"- {table}")

                    # List columns for each table
                    columns = inspector.get_columns(table)
                    for column in columns:
                        print(f"  - {column['name']} ({column['type']})")
            else:
                print("No tables found in the database.")

            connection.close()
            return 0

    except Exception as e:
        print(f"Error verifying database connection: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(verify_database_connection())
