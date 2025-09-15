"""CLI commands for user management."""

from __future__ import annotations

import click
from flask.cli import with_appcontext
from sqlalchemy import select

from app.auth.models import User
from app.extensions import db


@click.group("user")
def user_cli():
    """User management commands."""


def register_commands(app):
    """Register CLI commands with the application."""
    # Register the user command group
    app.cli.add_command(user_cli)

    # Add commands to the user group
    user_cli.add_command(list_users)
    user_cli.add_command(create_user)
    user_cli.add_command(update_user)
    user_cli.add_command(delete_user)
    user_cli.add_command(reset_admin_password)


@click.command("reset-password")
@click.option(
    "--email",
    prompt="User email",
    help="Email of the user to reset password for",
)
@click.option(
    "--password",
    prompt="New password",
    hide_input=True,
    confirmation_prompt=True,
    help="New password for the admin user",
)
@with_appcontext
def reset_admin_password(email: str, password: str) -> None:
    """Reset the password for an admin user.

    Args:
        email: Email of the admin user
        password: New password to set
    """
    user = db.session.scalar(select(User).filter_by(email=email, is_admin=True))

    if not user:
        click.echo(f"Error: No admin user found with email {email}")
        return

    try:
        user.set_password(password)
        db.session.commit()
        click.echo(f"Successfully updated password for admin user: {email}")
    except Exception as e:
        click.echo(f"Error updating password for admin user: {e}")
        db.session.rollback()


def _count_user_objects(user) -> dict[str, int]:
    """Count related objects for a user.

    Args:
        user: The User instance

    Returns:
        dict: Counts of related objects by type
    """
    return {
        "expenses": user.expenses.count(),
        "restaurants": user.restaurants.count(),
        "categories": user.categories.count(),
    }


@click.command("list")
@click.option(
    "--admin-only",
    is_flag=True,
    help="Show only admin users",
)
@click.option(
    "--objects",
    is_flag=True,
    help="Show count of related objects (expenses, restaurants, categories)",
)
@with_appcontext
def list_users(admin_only: bool, objects: bool) -> None:
    """List all users in the system.

    Args:
        admin_only: If True, only show admin users
        objects: If True, show count of related objects
    """
    query = select(User)
    if admin_only:
        query = query.where(User.is_admin.is_(True))

    users = db.session.scalars(query.order_by(User.email)).all()

    if not users:
        click.echo("No users found" + (" matching the criteria" if admin_only else ""))
        return

    # Prepare and display the table
    headers = ["ID", "Email", "Username", "Admin", "Active"]
    if objects:
        headers.extend(["Expenses", "Restaurants", "Categories"])

    rows = []
    for user in users:
        row = [
            str(user.id),
            user.email,
            user.username or "-",
            "✓" if user.is_admin else "",
            "✓" if user.is_active else "✗",
        ]

        if objects:
            counts = _count_user_objects(user)
            row.extend(
                [
                    str(counts["expenses"]),
                    str(counts["restaurants"]),
                    str(counts["categories"]),
                ]
            )

        rows.append(row)

    # Calculate column widths
    col_widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]

    # Print table
    click.echo(" " + " | ".join(f"{h.ljust(w)}" for h, w in zip(headers, col_widths)))
    click.echo("-" * (sum(col_widths) + 3 * (len(headers) - 1) + 2))

    for row in rows:
        click.echo(" " + " | ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths)))

    # Print summary
    summary = f"\nTotal users: {len(users)}" + (" (admin only)" if admin_only else "")
    if objects:
        total_counts = {
            "expenses": sum(int(row[5]) for row in rows),
            "restaurants": sum(int(row[6]) for row in rows),
            "categories": sum(int(row[7]) for row in rows),
        }
        summary += f"\nTotal objects: {total_counts['expenses']} expenses, "
        summary += f"{total_counts['restaurants']} restaurants, "
        summary += f"{total_counts['categories']} categories"

    click.echo(summary)


@click.command("create")
@click.option(
    "--username",
    prompt=True,
    help="Username for the new user",
)
@click.option(
    "--email",
    prompt=True,
    help="Email address for the new user",
)
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Password for the new user",
)
@click.option(
    "--admin",
    is_flag=True,
    default=False,
    help="Make the user an admin",
)
@click.option(
    "--active/--inactive",
    default=True,
    help="Set account active status (default: active)",
)
@with_appcontext
def create_user(username: str, email: str, password: str, admin: bool, active: bool = True) -> None:
    """Create a new user account.

    Args:
        username: Username for the new user
        email: Email address for the new user
        password: Password for the new user
        admin: Whether the user should have admin privileges
        active: Whether the account should be active
    """
    from sqlalchemy.exc import IntegrityError

    from app.auth.models import User

    # Validate email format
    if "@" not in email or "." not in email.split("@")[1]:
        click.echo("Error: Invalid email format", err=True)
        return

    # Password strength check
    if len(password) < 8:
        click.echo("Error: Password must be at least 8 characters long", err=True)
        return

    try:
        # Check if user with this email or username already exists
        if User.query.filter((User.email == email) | (User.username == username)).first():
            click.echo("Error: A user with this email or username already exists", err=True)
            return

        # Create the new user
        user = User(username=username, email=email, is_admin=admin, is_active=active)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        click.echo(f"Successfully created user: {username} ({email})")
        click.echo(f"  - Admin: {'Yes' if admin else 'No'}")
        click.echo(f"  - Active: {'Yes' if active else 'No'}")

    except IntegrityError as e:
        db.session.rollback()
        click.echo(f"Error creating user: {str(e)}", err=True)
    except Exception as e:
        db.session.rollback()
        click.echo(f"An unexpected error occurred: {str(e)}", err=True)


def _find_user_by_identifier(identifier: str) -> User | None:
    """Find a user by ID, username, or email.

    Args:
        identifier: User ID, username, or email

    Returns:
        User object if found, None otherwise
    """
    from app.auth.models import User

    if identifier.isdigit():
        return User.query.get(int(identifier))
    return User.query.filter((User.username == identifier) | (User.email == identifier)).first()


def _update_user_username(user: User, new_username: str, changes: list[str]) -> bool:
    """Update a user's username if it's available.

    Args:
        user: User object to update
        new_username: New username to set
        changes: List to track changes made

    Returns:
        bool: True if update was successful, False otherwise
    """
    from app.auth.models import User

    if new_username == user.username:
        return True

    if User.query.filter(User.username == new_username, User.id != user.id).first():
        click.echo(f"Error: Username '{new_username}' is already taken", err=True)
        return False

    changes.append(f"username to '{new_username}'")
    user.username = new_username
    return True


def _update_user_email(user: User, new_email: str, changes: list[str]) -> bool:
    """Update a user's email if it's valid and available.

    Args:
        user: User object to update
        new_email: New email to set
        changes: List to track changes made

    Returns:
        bool: True if update was successful, False otherwise
    """
    from app.auth.models import User

    if new_email == user.email:
        return True

    if "@" not in new_email or "." not in new_email.split("@")[1]:
        click.echo("Error: Invalid email format", err=True)
        return False

    if User.query.filter(User.email == new_email, User.id != user.id).first():
        click.echo(f"Error: Email '{new_email}' is already in use", err=True)
        return False

    changes.append(f"email to '{new_email}'")
    # Only update the email field, leave other fields unchanged
    user.email = new_email
    return True


def _update_user_password(user: User, changes: list[str]) -> bool:
    """Update a user's password.

    Args:
        user: User object to update
        changes: List to track changes made

    Returns:
        bool: True if update was successful, False otherwise
    """
    new_password = click.prompt("New password", hide_input=True, confirmation_prompt=True)
    if len(new_password) < 8:
        click.echo("Error: Password must be at least 8 characters long", err=True)
        return False

    if not click.confirm("Are you sure you want to update the password?"):
        click.echo("Password update cancelled.")
        return False

    user.set_password(new_password)
    changes.append("password")
    return True


def _update_user_admin_status(user: User, is_admin: bool, changes: list[str]) -> bool:
    """Update user's admin status.

    Args:
        user: User object to update
        is_admin: New admin status
        changes: List to track changes made

    Returns:
        bool: True if update was successful, False otherwise
    """
    if is_admin != user.is_admin:
        user.is_admin = is_admin
        status = "granted" if is_admin else "revoked"
        changes.append(f"admin privileges {status}")
    return True


def _update_user_active_status(user: User, is_active: bool, changes: list[str]) -> bool:
    """Update user's active status.

    Args:
        user: User object to update
        is_active: New active status
        changes: List to track changes made

    Returns:
        bool: True if update was successful, False otherwise
    """

    if is_active != user.is_active:
        user.is_active = is_active
        status = "activated" if is_active else "deactivated"
        changes.append(f"account {status}")
    return True


def _confirm_and_apply_changes(user: User, changes: list[str]) -> bool:
    """Confirm changes with the user and apply them to the database.

    Args:
        user: User object being updated
        changes: List of changes to be made

    Returns:
        bool: True if changes were applied, False otherwise
    """
    from sqlalchemy.exc import IntegrityError

    if not changes:
        click.echo("No changes specified. Use --help to see available options.")
        return False

    click.echo(f"The following changes will be made to user '{user.username}':")
    for change in changes:
        click.echo(f"  - {change}")

    if not click.confirm("Do you want to continue?"):
        click.echo("Update cancelled.")
        return False

    try:
        db.session.commit()
        click.echo(f"Successfully updated user: {user.username} " f"(ID: {user.id}, Email: {user.email})")
        return True
    except IntegrityError as e:
        db.session.rollback()
        click.echo(f"Error updating user: {str(e)}", err=True)
    except Exception as e:
        db.session.rollback()
        click.echo(f"An unexpected error occurred: {str(e)}", err=True)

    return False


@click.command("update")
@click.argument("user_identifier")
@click.option("--username", help="New username")
@click.option("--email", help="New email address")
@click.option(
    "--password",
    is_flag=True,
    help="Set to update password (will prompt for new password)",
)
@click.option(
    "--admin/--no-admin",
    default=None,
    help="Set or remove admin privileges",
)
@click.option(
    "--active/--inactive",
    default=True,
    help="Activate or deactivate the account",
)
@with_appcontext
def update_user(
    user_identifier: str,
    username: str | None = None,
    email: str | None = None,
    password: bool = False,
    admin: bool | None = None,
    active: bool | None = None,
) -> None:
    """Update an existing user's account information.

    The user can be identified by their ID, username, or email address.
    Only specified fields will be updated.
    """
    # Find the user
    user = _find_user_by_identifier(user_identifier)
    if not user:
        click.echo(f"Error: No user found with identifier: {user_identifier}", err=True)
        return
    changes = []

    click.echo(f"Updating user: {user.username} " f"(ID: {user.id}, Email: {user.email})")

    # Check if any changes are requested
    if not any([username, email, password, admin is not None, active is not None]):
        click.echo(
            "Error: No changes specified. Use --help to see available options.",
            err=True,
        )
        return

    # Update user attributes
    if username and not _update_user_username(user, username, changes):
        return
    if email and not _update_user_email(user, email, changes):
        return
    if password and not _update_user_password(user, changes):
        return
    if admin is not None and not _update_user_admin_status(user, admin, changes):
        return
    if active is not None and not _update_user_active_status(user, active, changes):
        return

    # Apply changes if any were made
    _confirm_and_apply_changes(user, changes)


def _display_user_info(user: User) -> None:
    """Display user information before deletion.

    Args:
        user: User object to display
    """
    click.echo(f"User to delete: {user.username} (ID: {user.id}, Email: {user.email})")
    click.echo(f"  - Admin: {'Yes' if user.is_admin else 'No'}")
    click.echo(f"  - Active: {'Yes' if user.is_active else 'No'}")


def _check_related_data(user: User, no_cascade: bool, force: bool) -> bool:
    """Check for related data and handle cascade options.

    Args:
        user: User object to check
        no_cascade: Whether to prevent deletion with related data
        force: Whether to skip confirmations

    Returns:
        bool: True if deletion should proceed, False otherwise
    """
    related_counts = _count_user_objects(user)
    has_related_data = any(count > 0 for count in related_counts.values())

    if has_related_data:
        click.echo("\nRelated data found:")
        for obj_type, count in related_counts.items():
            if count > 0:
                click.echo(f"  - {obj_type.capitalize()}: {count}")

        if no_cascade:
            click.echo(
                "\nError: User has related data and --no-cascade flag is set. "
                "Use --cascade to delete all related data, or remove the data first.",
                err=True,
            )
            return False

        if not force:
            if not click.confirm(
                f"\nThis will permanently delete the user and ALL {sum(related_counts.values())} related records. "
                "This action cannot be undone. Are you sure you want to continue?"
            ):
                click.echo("Deletion cancelled.")
                return False
    else:
        click.echo("\nNo related data found.")

    return True


def _confirm_deletion(user: User, force: bool) -> bool:
    """Confirm user deletion.

    Args:
        user: User object to delete
        force: Whether to skip confirmation

    Returns:
        bool: True if deletion should proceed, False otherwise
    """
    if not force:
        if not click.confirm(f"\nAre you sure you want to delete user '{user.username}'?"):
            click.echo("Deletion cancelled.")
            return False
    return True


def _execute_user_deletion(user: User) -> None:
    """Execute the actual user deletion.

    Args:
        user: User object to delete
    """
    from sqlalchemy.exc import IntegrityError

    try:
        # Store user info for confirmation message
        username = user.username
        user_id = user.id
        email = user.email
        related_counts = _count_user_objects(user)
        has_related_data = any(count > 0 for count in related_counts.values())

        # Delete the user (cascade will handle related data)
        db.session.delete(user)
        db.session.commit()

        click.echo(f"Successfully deleted user: {username} (ID: {user_id}, Email: {email})")
        if has_related_data:
            click.echo(f"Also deleted {sum(related_counts.values())} related records.")

    except IntegrityError as e:
        db.session.rollback()
        click.echo(f"Error deleting user: Database constraint violation - {str(e)}", err=True)
    except Exception as e:
        db.session.rollback()
        click.echo(f"An unexpected error occurred: {str(e)}", err=True)


@click.command("delete")
@click.argument("user_identifier")
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompts (use with caution)",
)
@click.option(
    "--cascade",
    is_flag=True,
    default=True,
    help="Delete all related data (expenses, restaurants, categories, tags) - default behavior",
)
@click.option(
    "--no-cascade",
    is_flag=True,
    help="Prevent deletion if user has related data",
)
@with_appcontext
def delete_user(
    user_identifier: str,
    force: bool = False,
    cascade: bool = True,
    no_cascade: bool = False,
) -> None:
    """Delete a user account and optionally all related data.

    The user can be identified by their ID, username, or email address.

    WARNING: This action cannot be undone! All user data will be permanently deleted.

    Args:
        user_identifier: User ID, username, or email address
        force: Skip confirmation prompts (dangerous!)
        cascade: Delete all related data (default: True)
        no_cascade: Prevent deletion if user has related data
    """
    # Find the user
    user = _find_user_by_identifier(user_identifier)
    if not user:
        click.echo(f"Error: No user found with identifier: {user_identifier}", err=True)
        return

    # Display user information
    _display_user_info(user)

    # Check related data and handle cascade options
    if not _check_related_data(user, no_cascade, force):
        return

    # Confirm deletion
    if not _confirm_deletion(user, force):
        return

    # Execute deletion
    _execute_user_deletion(user)
