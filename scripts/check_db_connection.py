#!/usr/bin/env python3
"""Script to verify database connection and list all tables with row counts."""

import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError


def main():
    # Database configuration - using the same settings as the app
    db_url = "sqlite:////home/mtd37/.meal_expense_tracker/meal_expenses.db"

    try:
        print(f"Connecting to database: {db_url}")
        engine = create_engine(db_url)

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ Successfully connected to the database")

            # Get database info
            inspector = inspect(engine)
            tables = inspector.get_table_names()

            print("\nTables in database:")
            for table in tables:
                # Get row count for each table
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"- {table}: {count} rows")

                # Show columns for each table
                columns = inspector.get_columns(table)
                print(f"  Columns: {', '.join(col['name'] for col in columns)}")

            # Check if migrations table exists and is up to date
            if "alembic_version" in tables:
                version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
                print(f"\n✓ Database is at migration version: {version}")
            else:
                print("\n⚠️  No alembic_version table found. Run 'flask db upgrade' to apply migrations.")

        return 0

    except SQLAlchemyError as e:
        print(f"\n❌ Database connection failed:")
        print(str(e))
        return 1
    except Exception as e:
        print(f"\n❌ An error occurred:")
        print(str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
