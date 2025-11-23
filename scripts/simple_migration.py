#!/usr/bin/env python3
"""
Simple Aurora Migration Script

Direct migration from RDS to Aurora using pg8000
"""

import json
import logging
import subprocess

import pg8000

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_credentials():
    """Get database credentials"""
    # Get RDS password from Secrets Manager
    rds_secret = json.loads(
        subprocess.run(
            [
                "aws",
                "secretsmanager",
                "get-secret-value",
                "--secret-id",
                "meal-expense-tracker/dev/db-credentials",
                "--query",
                "SecretString",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )

    return {
        "rds": {
            "host": "meal-expense-tracker-dev.ct7mmnmqbvyr.us-east-1.rds.amazonaws.com",
            "port": 5432,
            "database": "mealexpensetracker",
            "user": "db_mealexpensetracker",
            "password": rds_secret["password"],
        },
        "aurora": {
            "host": "meal-expense-tracker-dev-aurora.cluster-ct7mmnmqbvyr.us-east-1.rds.amazonaws.com",
            "port": 5432,
            "database": "mealexpensetracker",
            "user": "db_mealexpensetracker",
            "password": "xJKc1EAxLJarOHo6zAuH3zyk8yRxJbko",
        },
    }


def migrate_table(table_name, rds_conn, aurora_conn):
    """Migrate a single table"""
    logger.info(f"Migrating table: {table_name}")

    # Get table structure
    with rds_conn.cursor() as cursor:
        cursor.execute(
            f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position"
        )
        columns = cursor.fetchall()

    if not columns:
        logger.warning(f"No columns found for table {table_name}")
        return 0

    column_names = [col[0] for col in columns]
    select_sql = f"SELECT {', '.join(column_names)} FROM {table_name}"

    # Get data from RDS
    with rds_conn.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = cursor.fetchone()[0]

    logger.info(f"Table {table_name} has {total_rows} rows")

    if total_rows == 0:
        return 0

    # Create table in Aurora if it doesn't exist
    with aurora_conn.cursor() as cursor:
        create_table_sql = (
            f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join([f'{col[0]} {col[1]}' for col in columns])})"
        )
        cursor.execute(create_table_sql)
        aurora_conn.commit()

    # Migrate data in batches
    batch_size = 1000
    migrated = 0

    with rds_conn.cursor() as rds_cursor, aurora_conn.cursor() as aurora_cursor:
        rds_cursor.execute(select_sql)

        while True:
            rows = rds_cursor.fetchmany(batch_size)
            if not rows:
                break

            # Insert into Aurora
            placeholders = ", ".join(["%s"] * len(column_names))
            insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"

            aurora_cursor.executemany(insert_sql, rows)
            aurora_conn.commit()

            migrated += len(rows)
            logger.info(f"Migrated {migrated}/{total_rows} rows for {table_name}")

    return migrated


def main():
    """Main migration function"""
    logger.info("🚀 Starting Aurora migration")

    # Get credentials
    creds = get_credentials()

    # Connect to databases
    logger.info("Connecting to RDS...")
    rds_conn = pg8000.connect(**creds["rds"])

    logger.info("Connecting to Aurora...")
    aurora_conn = pg8000.connect(**creds["aurora"])

    try:
        # Tables to migrate
        tables = ["user", "category", "restaurant", "tag", "expense", "expense_tag"]

        total_migrated = 0
        for table in tables:
            try:
                migrated = migrate_table(table, rds_conn, aurora_conn)
                total_migrated += migrated
                logger.info(f"✅ Migrated {migrated} rows from {table}")
            except Exception as e:
                logger.error(f"❌ Failed to migrate {table}: {e}")

        logger.info(f"🎉 Migration complete! Total rows migrated: {total_migrated}")

    finally:
        rds_conn.close()
        aurora_conn.close()


if __name__ == "__main__":
    main()
