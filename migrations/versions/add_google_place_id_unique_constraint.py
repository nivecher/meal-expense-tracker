"""Add unique constraint for google_place_id per user

Revision ID: google_place_id_unique
Revises: d063f6577ecb
Create Date: 2024-01-15 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "google_place_id_unique"
down_revision = "d063f6577ecb"
branch_labels = None
depends_on = None


def upgrade():
    """Add unique constraint for google_place_id per user.

    This constraint prevents users from adding duplicate restaurants
    with the same Google Place ID.
    """
    # First, identify and handle any existing duplicates
    # This query finds duplicate google_place_id values per user
    connection = op.get_bind()

    # Check for existing duplicates
    duplicate_check = """
        SELECT user_id, google_place_id, COUNT(*) as count
        FROM restaurant
        WHERE google_place_id IS NOT NULL
        GROUP BY user_id, google_place_id
        HAVING COUNT(*) > 1
    """

    result = connection.execute(sa.text(duplicate_check)).fetchall()

    if result:
        print(f"Found {len(result)} duplicate google_place_id entries:")
        for row in result:
            print(f"  User {row.user_id}: google_place_id '{row.google_place_id}' appears {row.count} times")

        # For each duplicate group, keep the most recent one and mark others for deletion
        for user_id, google_place_id, count in result:
            print(f"Resolving duplicates for user {user_id}, google_place_id '{google_place_id}'")

            # Get all restaurant IDs for this duplicate group, ordered by creation date
            get_duplicates = """
                SELECT id, name, created_at
                FROM restaurant
                WHERE user_id = :user_id AND google_place_id = :google_place_id
                ORDER BY created_at DESC
            """

            duplicates = connection.execute(
                sa.text(get_duplicates), {"user_id": user_id, "google_place_id": google_place_id}
            ).fetchall()

            # Keep the first (most recent) and delete the rest
            if len(duplicates) > 1:
                keep_id = duplicates[0].id
                print(f"  Keeping restaurant ID {keep_id} ('{duplicates[0].name}', created {duplicates[0].created_at})")

                for duplicate in duplicates[1:]:
                    print(
                        f"  Deleting restaurant ID {duplicate.id} ('{duplicate.name}', created {duplicate.created_at})"
                    )

                    # First, update any expenses that reference this restaurant to point to the kept one
                    update_expenses = """
                        UPDATE expense
                        SET restaurant_id = :keep_id
                        WHERE restaurant_id = :delete_id
                    """
                    connection.execute(sa.text(update_expenses), {"keep_id": keep_id, "delete_id": duplicate.id})

                    # Then delete the duplicate restaurant
                    delete_restaurant = """
                        DELETE FROM restaurant
                        WHERE id = :delete_id
                    """
                    connection.execute(sa.text(delete_restaurant), {"delete_id": duplicate.id})

        print("Duplicate resolution completed.")
    else:
        print("No duplicate google_place_id entries found.")

    # Use batch mode for SQLite compatibility
    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.create_unique_constraint("uix_restaurant_google_place_id_user", ["user_id", "google_place_id"])

    print("Added unique constraint: uix_restaurant_google_place_id_user")


def downgrade():
    """Remove the unique constraint for google_place_id per user."""
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.drop_constraint("uix_restaurant_google_place_id_user", type_="unique")

    print("Removed unique constraint: uix_restaurant_google_place_id_user")
