"""CLI commands for user management."""

from __future__ import annotations

import click
from flask.cli import with_appcontext
from sqlalchemy import select

from app.auth.models import User
from app.extensions import db


def register_commands(app):
    """Register CLI commands with the application."""
    app.cli.add_command(reset_admin_password)
    app.cli.add_command(list_users)
    app.cli.add_command(create_user)
    app.cli.add_command(update_user)


@click.command("reset-admin-password")
@click.option(
    "--email",
    prompt="Admin email",
    help="Email of the admin user to reset password for",
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


@click.command("list-users")
@click.option(
    "--admin-only",
    is_flag=True,
    help="Show only admin users",
)
@with_appcontext
def list_users(admin_only: bool) -> None:
    """List all users in the system.

    Args:
        admin_only: If True, only show admin users
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
    # headers = ["ID", "Email", "Username", "Admin", "Active", "Last Login"]
    rows = []

    for user in users:
        rows.append(
            [
                str(user.id),
                user.email,
                user.username or "-",
                "✓" if user.is_admin else "",
                "✓" if user.is_active else "✗",
                # user.last_login_at.strftime("%Y-%m-%d %H:%M") if user.last_login_at else "Never"
            ]
        )

    # Calculate column widths
    col_widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]

    # Print table
    click.echo(" " + " | ".join(f"{h.ljust(w)}" for h, w in zip(headers, col_widths)))
    click.echo("-" * (sum(col_widths) + 3 * (len(headers) - 1) + 2))

    for row in rows:
        click.echo(" " + " | ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths)))

    click.echo(f"\nTotal users: {len(users)}" + (" (admin only)" if admin_only else ""))


@click.command("create-user")
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
def create_user(username: str, email: str, password: str, admin: bool, active: bool) -> None:
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


@click.command("update-user")
@click.argument("user_identifier")
@click.option(
    "--username",
    help="New username for the user",
)
@click.option(
    "--email",
    help="New email address for the user",
)
@click.option(
    "--password",
    help="New password for the user (will be prompted if not provided)",
    is_flag=True,
)
@click.option(
    "--admin/--no-admin",
    is_flag=True,
    default=None,
    help="Set or remove admin privileges",
)
@click.option(
    "--active/--inactive",
    is_flag=True,
    default=None,
    help="Set account active status",
)
@with_appcontext
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

    user.set_password(new_password)
    changes.append("password")
    return True


def _update_user_status(user: User, is_admin: bool | None, is_active: bool | None, changes: list[str]) -> None:
    """Update user's admin and active status.

    Args:
        user: User object to update
        is_admin: New admin status (None to keep current)
        is_active: New active status (None to keep current)
        changes: List to track changes made
    """
    if is_admin is not None and is_admin != user.is_admin:
        user.is_admin = is_admin
        status = "granted" if is_admin else "revoked"
        changes.append(f"admin privileges {status}")

    if is_active is not None and is_active != user.is_active:
        user.is_active = is_active
        status = "activated" if is_active else "deactivated"
        changes.append(f"account {status}")


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

    click.echo(f"The following changes will be made to user '{user.username}' (ID: {user.id}):")
    for change in changes:
        click.echo(f"  - {change}")

    if not click.confirm("Do you want to continue?"):
        click.echo("Update cancelled.")
        return False

    try:
        db.session.commit()
        click.echo(f"Successfully updated user: {user.username} (ID: {user.id})")
        return True
    except IntegrityError as e:
        db.session.rollback()
        click.echo(f"Error updating user: {str(e)}", err=True)
    except Exception as e:
        db.session.rollback()
        click.echo(f"An unexpected error occurred: {str(e)}", err=True)

    return False


def update_user(
    user_identifier: str,
    username: str | None,
    email: str | None,
    password: bool,
    admin: bool | None,
    active: bool | None,
) -> None:
    """Update an existing user's account information.

    The user can be identified by their ID, username, or email address.
    Only specified fields will be updated.

    Args:
        user_identifier: ID, username, or email of the user to update
        username: New username (if provided)
        email: New email (if provided)
        password: Whether to update the password (will prompt for new password)
        admin: Whether to make the user an admin
        active: Whether the account should be active
    """
    # Find the user
    user = _find_user_by_identifier(user_identifier)
    if not user:
        click.echo(f"Error: No user found with identifier: {user_identifier}", err=True)
        return

    changes = []

    # Update user attributes
    if username and not _update_user_username(user, username, changes):
        return

    if email and not _update_user_email(user, email, changes):
        return

    if password and not _update_user_password(user, changes):
        return

    _update_user_status(user, admin, active, changes)

    # Apply changes if any were made
    _confirm_and_apply_changes(user, changes)
