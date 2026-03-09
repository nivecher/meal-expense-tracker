"""CLI commands for merchant management."""

from __future__ import annotations

import csv
import io
import json
from typing import cast

import click
from flask import Flask
from flask.cli import with_appcontext

from app.auth.models import User
from app.merchants import services as merchant_services
from app.merchants.models import Merchant


@click.group("merchant", context_settings={"help_option_names": ["-h", "--help"]})
def merchant_cli() -> None:
    """Merchant management commands."""


def register_commands(app: Flask) -> None:
    """Register CLI commands with the application."""
    app.cli.add_command(merchant_cli)
    merchant_cli.add_command(list_merchants)
    merchant_cli.add_command(show_merchant)
    merchant_cli.add_command(categories_merchants)
    merchant_cli.add_command(export_merchants)
    merchant_cli.add_command(create_merchant_cmd)
    merchant_cli.add_command(delete_merchant_cmd)
    merchant_cli.add_command(link_merchant)


def _get_target_users(user_id: int | None, username: str | None, all_users: bool) -> list[User]:
    """Get target users based on options. Raises ClickException on failure."""
    if user_id is not None:
        from app.extensions import db

        user = db.session.get(User, user_id)
        if not user:
            raise click.ClickException(f"User with ID {user_id} not found")
        return [user]
    if username is not None:
        user = User.query.filter_by(username=username).first()
        if not user:
            raise click.ClickException(f"User with username '{username}' not found")
        return [user]
    if all_users:
        from app.extensions import db

        users = db.session.scalars(db.select(User)).all()
        if not users:
            raise click.ClickException("No users found in database")
        return cast(list[User], users)
    return []


def _merchant_to_dict(merchant: Merchant, detail_stats: dict | None = None) -> dict:
    """Build a dict for JSON/CSV output."""
    out = {
        "id": merchant.id,
        "name": merchant.name or "",
        "short_name": merchant.short_name or "",
        "category": merchant.category or "",
        "website": merchant.website or "",
    }
    if detail_stats is not None:
        out["restaurant_count"] = detail_stats.get("restaurant_count", 0)
        out["expense_count"] = detail_stats.get("expense_count", 0)
        out["total_amount"] = detail_stats.get("total_amount", 0)
    return out


def _display_merchant_line(
    merchant: Merchant,
    restaurant_count: int | None = None,
    detailed: bool = False,
    detail_stats: dict | None = None,
) -> None:
    """Print one merchant line (or block if detailed)."""
    count_str = f" ({restaurant_count} restaurants)" if restaurant_count is not None else ""
    click.echo(f"   🏪 {merchant.name} (ID: {merchant.id}){count_str}")
    if detailed:
        if merchant.short_name:
            click.echo(f"      Short name: {merchant.short_name}")
        if merchant.category:
            click.echo(f"      Category: {merchant.category}")
        if merchant.website:
            click.echo(f"      Website: {merchant.website}")
        if detail_stats:
            rest = detail_stats.get("restaurant_count", 0)
            exp = detail_stats.get("expense_count", 0)
            total = detail_stats.get("total_amount", 0)
            click.echo(f"      Restaurants: {rest}  |  Expenses: {exp}  |  Total: ${total:.2f}")


@click.command("list")
@click.option("--user-id", type=int, help="Show restaurant counts for this user ID")
@click.option("--username", type=str, help="Show restaurant counts for this username")
@click.option("--all-users", is_flag=True, help="Show merchants with restaurant counts per user")
@click.option("--search", "-q", type=str, help="Filter by name (case-insensitive substring)")
@click.option("--category", type=str, help="Filter by category (e.g. fast_food, coffee_shop)")
@click.option(
    "--detailed",
    is_flag=True,
    help="Show short_name, category, website, and restaurant/expense summary",
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["text", "json", "csv"]),
    default="text",
    help="Output format (default: text)",
)
@with_appcontext
def list_merchants(
    user_id: int | None,
    username: str | None,
    all_users: bool,
    search: str | None,
    category: str | None,
    detailed: bool,
    format_type: str,
) -> None:
    """List merchants. Optionally scope by user to show linked restaurant counts.

    Examples:
        flask merchant list
        flask merchant list --detailed
        flask merchant list --username admin
        flask merchant list --all-users --detailed
        flask merchant list -q "starbucks" --category coffee_shop
    """
    filters = {}
    if search:
        filters["search"] = search
    if category:
        filters["category"] = category

    if format_type != "text":
        if user_id is not None or username is not None or all_users:
            if sum(bool(x) for x in [user_id, username, all_users]) > 1:
                raise click.UsageError("Can only specify one of --user-id, --username, or --all-users")
            users = _get_target_users(user_id, username, all_users)
            merchants_by_user = []
            for user in users:
                merchants, data = merchant_services.get_merchants_with_detailed_stats(user.id, filters)
                merchant_data = data.get("merchant_data", {})
                rows = [_merchant_to_dict(m, merchant_data.get(m.id)) for m in merchants]
                stats = data.get("stats", {})
                merchants_by_user.append(
                    {
                        "username": user.username,
                        "user_id": user.id,
                        "merchants": rows,
                        "stats": stats,
                    }
                )
            if format_type == "json":
                click.echo(json.dumps({"users": merchants_by_user}, indent=2))
            else:
                fieldnames = [
                    "user_id",
                    "username",
                    "id",
                    "name",
                    "short_name",
                    "category",
                    "website",
                    "restaurant_count",
                    "expense_count",
                    "total_amount",
                ]
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for block in merchants_by_user:
                    for row in block["merchants"]:
                        writer.writerow(
                            {
                                "user_id": block["user_id"],
                                "username": block["username"],
                                **row,
                            }
                        )
                click.echo(buf.getvalue())
        else:
            merchants, data = merchant_services.get_merchants_with_detailed_stats(None, filters)
            merchant_data = data.get("merchant_data", {})
            rows = [_merchant_to_dict(m, merchant_data.get(m.id)) for m in merchants]
            stats = data.get("stats", {})
            if format_type == "json":
                click.echo(json.dumps({"merchants": rows, "stats": stats}, indent=2))
            else:
                fieldnames = [
                    "id",
                    "name",
                    "short_name",
                    "category",
                    "website",
                    "restaurant_count",
                    "expense_count",
                    "total_amount",
                ]
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
                click.echo(buf.getvalue())
        return

    if user_id is not None or username is not None or all_users:
        if sum(bool(x) for x in [user_id, username, all_users]) > 1:
            raise click.UsageError("Can only specify one of --user-id, --username, or --all-users")
        users = _get_target_users(user_id, username, all_users)
        click.echo("🏪 Merchants (restaurant counts by user):\n")
        for user in users:
            if detailed:
                merchants, data = merchant_services.get_merchants_with_detailed_stats(user.id, filters)
            else:
                merchants, data = merchant_services.get_merchants_with_stats(user.id, filters)
            merchant_data = data.get("merchant_data", {})
            click.echo(f"👤 {user.username} (ID: {user.id}) - {len(merchants)} merchants:")
            if merchants:
                for merchant in merchants:
                    info = merchant_data.get(merchant.id, {})
                    count = info.get("restaurant_count")
                    detail_stats = info if detailed else None
                    _display_merchant_line(
                        merchant,
                        restaurant_count=count,
                        detailed=detailed,
                        detail_stats=detail_stats,
                    )
            else:
                click.echo("   (No merchants)")
            if detailed and data.get("stats"):
                stats = data["stats"]
                click.echo(
                    f"   Summary: {stats.get('total_restaurants', 0)} restaurants, "
                    f"{stats.get('total_expenses', 0)} expenses, "
                    f"${stats.get('total_amount', 0):.2f} total"
                )
            click.echo()
        return

    if detailed:
        merchants, data = merchant_services.get_merchants_with_detailed_stats(None, filters)
        merchant_data = data.get("merchant_data", {})
        click.echo(f"🏪 Merchants: {len(merchants)}\n")
        for merchant in merchants:
            detail_stats = merchant_data.get(merchant.id)
            rest_count = detail_stats.get("restaurant_count") if detail_stats else None
            _display_merchant_line(
                merchant,
                restaurant_count=rest_count,
                detailed=True,
                detail_stats=detail_stats,
            )
        if data.get("stats"):
            stats = data["stats"]
            click.echo(
                f"Summary: {stats.get('total_restaurants', 0)} restaurants, "
                f"{stats.get('total_expenses', 0)} expenses, "
                f"${stats.get('total_amount', 0):.2f} total"
            )
    else:
        merchants = merchant_services.get_merchants(0, filters)
        click.echo(f"🏪 Merchants: {len(merchants)}\n")
        for merchant in merchants:
            _display_merchant_line(merchant, detailed=False)


@click.command("show")
@click.argument("merchant_id", type=int)
@click.option("--user-id", type=int, help="Show linked restaurants for this user only")
@click.option("--username", type=str, help="Show linked restaurants for this username")
@click.option(
    "--detailed",
    is_flag=True,
    help="Show restaurant and expense summary (counts and total amount)",
)
@click.option(
    "--unlinked",
    is_flag=True,
    help="Show unlinked restaurants matching this merchant (requires --user-id or --username)",
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (default: text)",
)
@with_appcontext
def show_merchant(
    merchant_id: int,
    user_id: int | None,
    username: str | None,
    detailed: bool,
    unlinked: bool,
    format_type: str,
) -> None:
    """Show one merchant by ID and optionally linked restaurants for a user.

    Examples:
        flask merchant show 1
        flask merchant show 1 --username admin
        flask merchant show 1 --detailed
    """
    merchant = merchant_services.get_merchant(merchant_id)
    if not merchant:
        raise click.ClickException(f"Merchant with ID {merchant_id} not found")

    if format_type == "json":
        payload = {
            "id": merchant.id,
            "name": merchant.name or "",
            "short_name": merchant.short_name or "",
            "category": merchant.category or "",
            "website": merchant.website or "",
        }
        if user_id is not None or username is not None:
            users = _get_target_users(user_id, username, False)
            users_payload: list[dict[str, object]] = []
            payload["users"] = users_payload
            for user in users:
                restaurants = merchant_services.get_restaurants_for_merchant(user.id, merchant_id)
                summary = merchant_services.get_merchant_expense_summary(user.id, merchant_id)
                block = {
                    "username": user.username,
                    "user_id": user.id,
                    "restaurants": [{"id": r.id, "name": r.name or ""} for r in restaurants],
                    "expense_summary": summary,
                }
                if unlinked:
                    unlinked_rest = merchant_services.get_unlinked_matching_restaurants_for_merchant(
                        user.id, merchant_id
                    )
                    block["unlinked"] = [{"id": r.id, "name": r.name or ""} for r in unlinked_rest]
                users_payload.append(block)
        else:
            count = len(list(merchant.restaurants))
            payload["total_linked_restaurants"] = count
            payload["expense_summary"] = merchant_services.get_merchant_expense_summary(None, merchant_id)
        click.echo(json.dumps(payload, indent=2))
        return

    click.echo(f"🏪 {merchant.name} (ID: {merchant.id})")
    if merchant.short_name:
        click.echo(f"   Short name: {merchant.short_name}")
    if merchant.category:
        click.echo(f"   Category: {merchant.category}")
    if merchant.website:
        click.echo(f"   Website: {merchant.website}")
    click.echo()

    if user_id is not None or username is not None:
        users = _get_target_users(user_id, username, False)
        for user in users:
            restaurants = merchant_services.get_restaurants_for_merchant(user.id, merchant_id)
            click.echo(f"👤 {user.username} (ID: {user.id}) - {len(restaurants)} linked restaurants:")
            for rest in restaurants:
                click.echo(f"   - {rest.name} (ID: {rest.id})")
            if detailed:
                summary = merchant_services.get_merchant_expense_summary(user.id, merchant_id)
                click.echo(
                    f"   Expense summary: {summary['expense_count']} expenses, " f"${summary['total_amount']:.2f} total"
                )
            if unlinked:
                unlinked_rest = merchant_services.get_unlinked_matching_restaurants_for_merchant(user.id, merchant_id)
                click.echo(f"   Unlinked matching restaurants: {len(unlinked_rest)}")
                if unlinked_rest:
                    for rest in unlinked_rest:
                        click.echo(f"   - {rest.name} (ID: {rest.id})")
                else:
                    click.echo("   (No unlinked matches)")
            click.echo()
    elif unlinked:
        raise click.UsageError("--unlinked requires --user-id or --username")
    else:
        # Show total linked restaurants across all users (count from relationship)
        count = len(list(merchant.restaurants))
        click.echo(f"   Total linked restaurants (all users): {count}")
        if detailed:
            summary = merchant_services.get_merchant_expense_summary(None, merchant_id)
            click.echo(
                f"   Expense summary: {summary['expense_count']} expenses, " f"${summary['total_amount']:.2f} total"
            )


@click.command("categories")
@with_appcontext
def categories_merchants() -> None:
    """List valid merchant categories for use with --category filter."""
    categories = merchant_services.get_merchant_categories()
    click.echo("Valid categories:")
    for cat in categories:
        click.echo(f"  {cat}")


@click.command("export")
@click.option("--user-id", type=int, help="Export merchants for this user ID")
@click.option("--username", type=str, help="Export merchants for this username")
@click.option("--format", "format_type", type=click.Choice(["csv", "json"]), default="csv")
@click.option("--output", "-o", type=click.Path(writable=True, path_type=str), help="Output file path")
@click.option("--ids", type=str, help="Comma-separated merchant IDs to export (default: all for user)")
@with_appcontext
def export_merchants(
    user_id: int | None,
    username: str | None,
    format_type: str,
    output: str | None,
    ids: str | None,
) -> None:
    """Export merchants as CSV or JSON. Requires --user-id or --username."""
    if not user_id and not username:
        raise click.UsageError("Must specify --user-id or --username")
    if user_id and username:
        raise click.UsageError("Can only specify one of --user-id or --username")
    users = _get_target_users(user_id, username, False)
    user = users[0]
    merchant_ids = None
    if ids:
        try:
            merchant_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
        except ValueError:
            raise click.ClickException("--ids must be comma-separated integers")
    rows = merchant_services.export_merchants_for_user(user.id, merchant_ids)
    if not rows:
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write("")
        return
    if format_type == "json":
        out = json.dumps(rows, indent=2)
    else:
        fieldnames = [
            "name",
            "short_name",
            "website",
            "category",
            "restaurant_count",
            "created_at",
            "updated_at",
        ]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()
        writer.writerows(rows)
        out = buf.getvalue()
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        click.echo(out)


@click.command("create")
@click.option("--user-id", type=int, help="User context for creation")
@click.option("--username", type=str, help="Username for creation")
@click.option("--name", type=str, required=True, help="Merchant name")
@click.option("--short-name", type=str, help="Short display name")
@click.option("--category", type=str, help="Category (use 'flask merchant categories' for list)")
@click.option("--website", type=str, help="Website URL")
@with_appcontext
def create_merchant_cmd(
    user_id: int | None,
    username: str | None,
    name: str,
    short_name: str | None,
    category: str | None,
    website: str | None,
) -> None:
    """Create a new merchant. Requires --user-id or --username."""
    if not user_id and not username:
        raise click.UsageError("Must specify --user-id or --username")
    if user_id and username:
        raise click.UsageError("Can only specify one of --user-id or --username")
    users = _get_target_users(user_id, username, False)
    user = users[0]
    if category is not None:
        valid = merchant_services.get_merchant_categories()
        if category not in valid:
            raise click.UsageError(f"Invalid category '{category}'. Valid: {', '.join(valid)}")
    data = {"name": name}
    if short_name is not None:
        data["short_name"] = short_name
    if category is not None:
        data["category"] = category
    if website is not None:
        data["website"] = website
    try:
        merchant = merchant_services.create_merchant(user.id, data)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    click.echo(f"Created merchant: {merchant.name} (ID: {merchant.id})")


@click.command("delete")
@click.argument("merchant_id", type=int)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@with_appcontext
def delete_merchant_cmd(merchant_id: int, force: bool) -> None:
    """Delete a merchant by ID."""
    merchant = merchant_services.get_merchant(merchant_id)
    if not merchant:
        raise click.ClickException(f"Merchant with ID {merchant_id} not found")
    if not force:
        click.confirm(
            f"Delete merchant '{merchant.name}' (ID: {merchant_id})?",
            default=False,
            abort=True,
        )
    merchant_services.delete_merchant(merchant_id)
    click.echo(f"Deleted merchant ID {merchant_id}")


@click.command("link")
@click.argument("merchant_id", type=int)
@click.option("--user-id", type=int, help="User whose restaurants to link")
@click.option("--username", type=str, help="Username whose restaurants to link")
@click.option(
    "--restaurant-ids",
    type=str,
    help="Comma-separated restaurant IDs to link (default: all matching unlinked)",
)
@click.option("--dry-run", is_flag=True, help="Only report what would be linked")
@with_appcontext
def link_merchant(
    merchant_id: int,
    user_id: int | None,
    username: str | None,
    restaurant_ids: str | None,
    dry_run: bool,
) -> None:
    """Link unlinked restaurants to a merchant. Requires --user-id or --username."""
    if not user_id and not username:
        raise click.UsageError("Must specify --user-id or --username")
    if user_id and username:
        raise click.UsageError("Can only specify one of --user-id or --username")
    merchant = merchant_services.get_merchant(merchant_id)
    if not merchant:
        raise click.ClickException(f"Merchant with ID {merchant_id} not found")
    users = _get_target_users(user_id, username, False)
    user = users[0]
    candidates = merchant_services.get_unlinked_matching_restaurants_for_merchant(user.id, merchant_id)
    if not candidates:
        raise click.ClickException(f"No unlinked matching restaurants found for merchant {merchant_id}")
    ids_list = None
    if restaurant_ids:
        try:
            ids_list = [int(x.strip()) for x in restaurant_ids.split(",") if x.strip()]
        except ValueError:
            raise click.ClickException("--restaurant-ids must be comma-separated integers")
        allowed = {r.id for r in candidates if r.id is not None}
        ids_list = [i for i in ids_list if i in allowed]
    if dry_run:
        to_link = candidates if ids_list is None else [r for r in candidates if r.id in (ids_list or [])]
        click.echo(f"Would link {len(to_link)} restaurant(s) to {merchant.name} (ID: {merchant_id})")
        for r in to_link:
            click.echo(f"  - {r.name} (ID: {r.id})")
        return
    count, linked = merchant_services.associate_unlinked_matching_restaurants(user.id, merchant_id, ids_list)
    click.echo(f"Linked {count} restaurant(s) to {merchant.name} (ID: {merchant_id})")
    for r in linked:
        click.echo(f"  - {r.name} (ID: {r.id})")
