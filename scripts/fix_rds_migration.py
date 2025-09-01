#!/usr/bin/env python3
"""
Fix RDS migration history for existing tables.

This script connects directly to RDS and fixes the migration history
when you have existing tables but no migration history.
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


def fix_rds_migration_history():
    """Fix migration history for RDS database."""
    app = create_app()

    with app.app_context():
        try:
            print("🔍 Checking database state...")

            # Check if alembic_version table exists
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()

            print(f"📋 Existing tables: {existing_tables}")

            if "alembic_version" in existing_tables:
                print("✅ alembic_version table already exists")

                # Check current revision
                try:
                    result = db.session.execute(text("SELECT version_num FROM alembic_version"))
                    current_revision = result.scalar()
                    print(f"📋 Current revision: {current_revision}")
                except Exception as e:
                    print(f"⚠️  Could not read current revision: {e}")
                    current_revision = None

                if current_revision:
                    print("✅ Migration history appears to be intact")
                    return
                else:
                    print("⚠️  alembic_version table exists but is empty")

            # Get the latest migration revision
            print("🔍 Getting migration history...")
            from flask_migrate import history

            migration_history = history()
            if not migration_history:
                print("❌ No migration history found")
                return

            latest_revision = migration_history[-1].revision
            print(f"📋 Latest migration revision: {latest_revision}")

            # Create alembic_version table if it doesn't exist
            if "alembic_version" not in existing_tables:
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
                print("✅ alembic_version table created")
            else:
                print("🔧 alembic_version table already exists, clearing it...")
                db.session.execute(text("DELETE FROM alembic_version"))

            # Insert the current revision
            print(f"🔧 Setting revision to: {latest_revision}")
            db.session.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"), {"revision": latest_revision}
            )

            db.session.commit()
            print(f"✅ Migration history fixed. Set to revision: {latest_revision}")

            # Verify the fix
            result = db.session.execute(text("SELECT version_num FROM alembic_version"))
            verified_revision = result.scalar()
            print(f"✅ Verified revision: {verified_revision}")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error fixing migration history: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    fix_rds_migration_history()
