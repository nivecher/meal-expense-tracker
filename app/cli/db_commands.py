"""Database CLI commands (init, run-migrations, stamp).

These commands run locally or proxy to Lambda when flask --remote is used.
"""

from __future__ import annotations

import click
from flask import Flask
from flask.cli import with_appcontext


@click.group("db", context_settings={"help_option_names": ["-h", "--help"]})
def db_cli() -> None:
    """Database operations (init, migrations, stamp)."""


def register_commands(app: Flask) -> None:
    """Register db CLI commands. Add to existing flask db group from Flask-Migrate."""
    db_cmd = app.cli.get_command(None, "db")
    if db_cmd and hasattr(db_cmd, "add_command"):
        db_cmd.add_command(db_init)
        db_cmd.add_command(db_run_migrations)
        db_cmd.add_command(db_stamp)
    else:
        # Fallback: create our own db group if Flask-Migrate not loaded
        app.cli.add_command(db_cli)
        db_cli.add_command(db_init)
        db_cli.add_command(db_run_migrations)
        db_cli.add_command(db_stamp)


@click.command("init")
@click.option("--force", is_flag=True, help="Force recreation of existing database")
@click.option("--sample-data", is_flag=True, help="Create sample data")
@with_appcontext
def db_init(force: bool, sample_data: bool) -> None:
    """Initialize database schema and create default data."""
    from init_db import init_db

    success = init_db(drop_all=force)
    if success:
        click.echo("✅ Database initialized successfully")
    else:
        click.echo("❌ Database initialization failed", err=True)
        raise SystemExit(1)


@click.command("run-migrations")
@click.option("--dry-run", is_flag=True, help="Show what migrations would be applied")
@click.option("--target-revision", type=str, help="Specific migration revision to run to")
@click.option("--fix-history", is_flag=True, help="Fix migration history for existing tables")
@with_appcontext
def db_run_migrations(dry_run: bool, target_revision: str | None, fix_history: bool) -> None:
    """Run database migrations (same as migrate_db)."""
    from app.utils.migration_manager import migration_manager

    if fix_history:
        result = migration_manager.fix_migration_history()
        if not result.get("success"):
            click.echo(f"❌ Fix history failed: {result.get('error')}", err=True)
            raise SystemExit(1)

    result = migration_manager.run_migrations(
        dry_run=dry_run,
        target_revision=target_revision,
    )
    if result.get("success"):
        click.echo("✅ Migrations completed successfully")
    else:
        click.echo(f"❌ Migrations failed: {result.get('message', 'Unknown error')}", err=True)
        raise SystemExit(1)


@click.command("stamp")
@click.option("--revision", required=True, help="Target revision to stamp to")
@with_appcontext
def db_stamp(revision: str) -> None:
    """Stamp the database to a specific Alembic revision."""
    from flask_migrate import stamp

    stamp(revision=revision)
    click.echo(f"✅ Stamped database to revision {revision}")
