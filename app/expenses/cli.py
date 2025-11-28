"""CLI commands for expense and category management."""

from __future__ import annotations

from typing import cast

import click
from flask import Flask, current_app
from flask.cli import with_appcontext

from app.auth.models import User
from app.constants.categories import get_default_categories
from app.expenses.models import Category
from app.extensions import db


@click.group("category")
def category_cli() -> None:
    """Category management commands."""


def register_commands(app: Flask) -> None:
    """Register CLI commands with the application."""
    # Register the category command group
    app.cli.add_command(category_cli)

    # Add commands to the category group
    category_cli.add_command(reinit_categories)
    category_cli.add_command(list_categories)


def _sort_categories_by_default_order(categories: list[Category]) -> list[Category]:
    """Sort categories according to the default definition order."""
    default_categories = get_default_categories()
    default_names = [cat["name"] for cat in default_categories]

    # Create a mapping of category name to order index
    name_to_order = {name: i for i, name in enumerate(default_names)}

    # Sort categories: default categories first (in original order), then others
    def sort_key(cat: Category) -> tuple[int, int | str]:
        category_name = cat.name or ""
        if category_name in name_to_order:
            return (0, name_to_order[category_name])  # Default categories first
        else:
            return (1, category_name)  # Custom categories after, alphabetically

    return sorted(categories, key=sort_key)


def _get_target_users(user_id: int | None, username: str | None, all_users: bool) -> list[User]:
    """Get target users based on options."""
    if user_id:
        from app.extensions import db

        user = db.session.get(User, user_id)
        if not user:
            click.echo(f"❌ Error: User with ID {user_id} not found")
            return []
        return [user]
    elif username:
        user = User.query.filter_by(username=username).first()
        if not user:
            click.echo(f"❌ Error: User with username '{username}' not found")
            return []
        return [user]
    elif all_users:
        from app.extensions import db

        users = db.session.scalars(db.select(User)).all()
        if not users:
            click.echo("❌ Error: No users found in database")
            return []
        return cast(list[User], users)
    return []


def _process_users(users: list[User], force: bool, dry_run: bool) -> tuple[int, int]:
    """Process users and update their categories."""
    default_categories = get_default_categories()
    total_created = 0
    total_deleted = 0

    for user in users:
        click.echo(f"\n👤 Processing user: {user.username} (ID: {user.id})")

        # Get current categories
        current_categories = Category.query.filter_by(user_id=user.id).all()
        current_names = {c.name for c in current_categories}

        click.echo(f"   Current categories: {len(current_categories)}")

        if force and current_categories:
            # Delete existing categories
            click.echo(
                f"   🗑️  {'Would delete' if dry_run else 'Deleting'} " f"{len(current_categories)} existing categories"
            )
            if not dry_run:
                for cat in current_categories:
                    db.session.delete(cat)

                # Flush the deletions to ensure they're committed before adding new ones
                db.session.flush()
                total_deleted += len(current_categories)
            current_names = set()

        # Add missing categories
        categories_to_add = [cat for cat in default_categories if cat["name"] not in current_names]

        if categories_to_add:
            click.echo(f"   ➕ {'Would add' if dry_run else 'Adding'} " f"{len(categories_to_add)} categories")
            if not dry_run:
                for cat_data in categories_to_add:
                    new_category = Category(
                        user_id=user.id,
                        name=cat_data["name"],
                        description=cat_data["description"],
                        color=cat_data["color"],
                        icon=cat_data["icon"],
                        is_default=True,
                    )
                    db.session.add(new_category)
            total_created += len(categories_to_add)
        else:
            click.echo("   ✅ No missing categories")

    return total_created, total_deleted


def _show_results(total_created: int, total_deleted: int, force: bool, dry_run: bool) -> None:
    """Show final results."""
    if not dry_run:
        try:
            db.session.commit()
            click.echo("\n✅ Success!")
            click.echo(f"   📊 Categories created: {total_created}")
            if force:
                click.echo(f"   🗑️  Categories deleted: {total_deleted}")
        except Exception as e:
            db.session.rollback()
            click.echo(f"\n❌ Error committing changes: {e}")
            click.echo("   🔄 All changes have been rolled back")
            current_app.logger.error(f"Error reinitializing categories: {e}")
            raise  # Re-raise so CLI shows proper exit code
    else:
        click.echo("\n🔍 Dry run complete!")
        click.echo(f"   📊 Would create: {total_created} categories")
        if force:
            click.echo(f"   🗑️  Would delete: {total_deleted} categories")


@click.command("reinit")
@click.option("--user-id", type=int, help="Specific user ID to reinitialize categories for")
@click.option("--username", type=str, help="Specific username to reinitialize categories for")
@click.option("--all-users", is_flag=True, help="Reinitialize categories for all users")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@click.option("--force", is_flag=True, help="Remove existing categories and recreate them")
@with_appcontext
def reinit_categories(user_id: int | None, username: str | None, all_users: bool, dry_run: bool, force: bool) -> None:
    """Reinitialize expense categories for users.

    Examples:
        flask category reinit --user-id 1
        flask category reinit --username admin
        flask category reinit --all-users
        flask category reinit --all-users --dry-run
        flask category reinit --user-id 1 --force
    """
    # Validate options
    if not any([user_id, username, all_users]):
        click.echo("❌ Error: Must specify --user-id, --username, or --all-users")
        return

    if sum(bool(x) for x in [user_id, username, all_users]) > 1:
        click.echo("❌ Error: Can only specify one of --user-id, --username, or --all-users")
        return

    # Get target users
    users = _get_target_users(user_id, username, all_users)
    if not users:
        return

    # Show summary
    click.echo(f"🎯 Target: {len(users)} user(s)")
    for user in users:
        click.echo(f"   - {user.username} (ID: {user.id})")

    if dry_run:
        click.echo("\n🔍 DRY RUN MODE - No changes will be made\n")

    # Process users
    total_created, total_deleted = _process_users(users, force, dry_run)

    # Show results
    _show_results(total_created, total_deleted, force, dry_run)


@click.command("list")
@click.option("--user-id", type=int, help="Specific user ID to show categories for")
@click.option("--username", type=str, help="Specific username to show categories for")
@click.option("--all-users", is_flag=True, help="Show categories for all users")
@with_appcontext
def list_categories(user_id: int | None, username: str | None, all_users: bool) -> None:
    """List expense categories for users.

    Examples:
        flask category list --user-id 1
        flask category list --username admin
        flask category list --all-users
    """
    if not any([user_id, username, all_users]):
        click.echo("❌ Error: Must specify --user-id, --username, or --all-users")
        return

    # Get target users
    users = _get_target_users(user_id, username, all_users)
    if not users:
        return

    click.echo(f"📋 Categories for {len(users)} user(s):\n")

    for user in users:
        categories = Category.query.filter_by(user_id=user.id).all()
        # Sort categories to match the original definition order
        categories = _sort_categories_by_default_order(categories)
        click.echo(f"👤 {user.username} (ID: {user.id}) - {len(categories)} categories:")

        if categories:
            for cat in categories:
                default_flag = " [DEFAULT]" if cat.is_default else ""
                color_info = f" ({cat.color})" if cat.color else ""
                icon_info = f" 🎨{cat.icon}" if cat.icon else ""
                click.echo(f"   - {cat.name}{default_flag}{color_info}{icon_info}")
                if cat.description:
                    click.echo(f"     {cat.description}")
        else:
            click.echo("   (No categories)")
        click.echo()
