#!/usr/bin/env python3
"""
Fix migration history for existing tables.

This script creates the alembic_version table and sets it to the latest migration
revision when you have existing tables but no migration history.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import current_app
from sqlalchemy import text

from app import create_app
from app.extensions import db


def fix_migration_history():
    """Fix migration history for existing tables."""
    app = create_app()

    with app.app_context():
        try:
            # Check if alembic_version table exists
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()

            if "alembic_version" in existing_tables:
                print("✅ alembic_version table already exists")
                return

            # Get the latest migration revision
            from flask_migrate import history

            migration_history = history()
            if not migration_history:
                print("❌ No migration history found")
                return

            latest_revision = migration_history[-1].revision
            print(f"📋 Latest migration revision: {latest_revision}")

            # Create alembic_version table
            print("🔧 Creating alembic_version table...")
            db.session.execute(
                text(
                    """
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """
                )
            )

            # Insert the current revision
            db.session.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"), {"revision": latest_revision}
            )

            db.session.commit()
            print(f"✅ Migration history fixed. Set to revision: {latest_revision}")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error fixing migration history: {e}")
            sys.exit(1)


if __name__ == "__main__":
    fix_migration_history()
