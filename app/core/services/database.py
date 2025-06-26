"""Database service layer for the Meal Expense Tracker application.

This module provides a service layer for database operations, including:
- Database initialization
- Schema migrations
- Database health checks
- Connection management
"""

from typing import Any, Dict, List

from sqlalchemy import inspect

from app.core.exceptions import DatabaseError
from app.extensions import db


def get_tables() -> List[str]:
    """Get a list of all tables in the database.

    Returns:
        List[str]: List of table names

    Raises:
        DatabaseError: If there's an error connecting to the database
    """
    try:
        inspector = inspect(db.engine)
        return inspector.get_table_names()
    except Exception as e:
        raise DatabaseError(f"Failed to get database tables: {str(e)}") from e


def check_connection() -> Dict[str, Any]:
    """Check if the database connection is working.

    Returns:
        Dict[str, Any]: Status information about the database connection

    Raises:
        DatabaseError: If the database connection fails
    """
    try:
        # Test the connection by getting the list of tables
        tables = get_tables()
        return {
            "status": "success",
            "tables": tables,
            "table_count": len(tables),
            "connection": str(db.engine.url),
        }
    except Exception as e:
        raise DatabaseError(f"Database connection failed: {str(e)}") from e


def run_migrations() -> Dict[str, Any]:
    """Run database migrations.

    Returns:
        Dict[str, Any]: Status of the migration

    Raises:
        DatabaseError: If migrations fail
    """
    try:
        from migrate_db import run_migrations as _run_migrations

        _run_migrations()
        return {"status": "success", "message": "Migrations completed successfully"}
    except Exception as e:
        raise DatabaseError(f"Migration failed: {str(e)}") from e


def reset_database() -> Dict[str, Any]:
    """Reset the database (drop all tables and re-run migrations).

    WARNING: This will delete all data in the database!

    Returns:
        Dict[str, Any]: Status of the reset operation

    Raises:
        DatabaseError: If the reset fails
    """
    try:
        from migrate_db import reset_database as _reset_database

        _reset_database()
        return {"status": "success", "message": "Database reset completed successfully"}
    except Exception as e:
        raise DatabaseError(f"Database reset failed: {str(e)}") from e
