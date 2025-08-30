"""CLI commands for restaurant management."""

from __future__ import annotations

import click
from flask import current_app
from flask.cli import with_appcontext

from app.auth.models import User
from app.extensions import db
from app.restaurants.models import Restaurant


@click.group("restaurant")
def restaurant_cli():
    """Restaurant management commands."""


def register_commands(app):
    """Register CLI commands with the application."""
    # Register the restaurant command group
    app.cli.add_command(restaurant_cli)

    # Add commands to the restaurant group
    restaurant_cli.add_command(list_restaurants)
    restaurant_cli.add_command(validate_restaurants)


def _get_target_users(user_id: int | None, username: str | None, all_users: bool) -> list[User]:
    """Get target users based on options."""
    if user_id:
        user = User.query.get(user_id)
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
        users = User.query.all()
        if not users:
            click.echo("❌ Error: No users found in database")
            return []
        return users
    return []


def _validate_restaurant_with_google(restaurant: Restaurant) -> dict:
    """Validate restaurant information using Google Places API directly.

    Args:
        restaurant: Restaurant instance to validate

    Returns:
        Dictionary with validation results
    """
    try:
        # Import Google Maps client
        from app.api.routes import get_gmaps_client

        if restaurant.google_place_id:
            # Call the Google Places API directly
            gmaps = get_gmaps_client()
            if not gmaps:
                return {"valid": False, "errors": ["Google Maps API not configured"]}

            place = gmaps.place(
                place_id=restaurant.google_place_id,
                language="en",
                fields=[
                    "name",
                    "formatted_address",
                    "geometry/location",
                    "rating",
                    "business_status",
                    "type",  # Use 'type' instead of 'types'
                    "user_ratings_total",
                    "opening_hours",
                    "website",
                    "international_phone_number",
                    "price_level",
                    "editorial_summary",
                ],
            )

            if place and "result" in place:
                google_data = place["result"]

                return {
                    "valid": True,
                    "google_name": google_data.get("name"),
                    "google_address": google_data.get("formatted_address"),
                    "google_rating": google_data.get("rating"),
                    "google_status": google_data.get("business_status"),
                    "types": google_data.get("type", []),  # Use 'type' field
                    "google_phone": google_data.get("international_phone_number"),
                    "google_website": google_data.get("website"),
                    "google_price_level": google_data.get("price_level"),
                    "google_address_components": google_data.get("address_components", []),
                    "google_street_number": next(
                        (
                            comp.get("long_name")
                            for comp in google_data.get("address_components", [])
                            if "street_number" in comp.get("types", [])
                        ),
                        None,
                    ),
                    "google_route": next(
                        (
                            comp.get("long_name")
                            for comp in google_data.get("address_components", [])
                            if "route" in comp.get("types", [])
                        ),
                        None,
                    ),
                    "google_city": next(
                        (
                            comp.get("long_name")
                            for comp in google_data.get("address_components", [])
                            if "locality" in comp.get("types", [])
                        ),
                        None,
                    ),
                    "google_state": next(
                        (
                            comp.get("short_name")
                            for comp in google_data.get("address_components", [])
                            if "administrative_area_level_1" in comp.get("types", [])
                        ),
                        None,
                    ),
                    "google_postal_code": next(
                        (
                            comp.get("long_name")
                            for comp in google_data.get("address_components", [])
                            if "postal_code" in comp.get("types", [])
                        ),
                        None,
                    ),
                    "google_country": next(
                        (
                            comp.get("long_name")
                            for comp in google_data.get("address_components", [])
                            if "country" in comp.get("types", [])
                        ),
                        None,
                    ),
                    "errors": [],
                }
            elif place and "status" in place:
                # Google API returned an error status
                status = place["status"]
                error_msg = place.get("error_message", f"Google API error: {status}")
                return {"valid": False, "errors": [error_msg]}
            else:
                return {"valid": False, "errors": ["No response from Google Places API"]}
        else:
            # No Google Place ID to validate
            return {"valid": None, "errors": ["No Google Place ID available for validation"]}

    except ImportError:
        return {"valid": False, "errors": ["Google Places API service not available"]}
    except Exception as e:
        current_app.logger.error(f"Error validating restaurant {restaurant.id}: {str(e)}")
        return {"valid": False, "errors": [f"Unexpected error: {str(e)}"]}


def _get_user_restaurants(user: User, with_google_id: bool) -> list[Restaurant]:
    """Get restaurants for a user with optional filtering."""
    query = Restaurant.query.filter_by(user_id=user.id)
    if with_google_id:
        query = query.filter(Restaurant.google_place_id.isnot(None))
    return query.order_by(Restaurant.name).all()


def _format_restaurant_detailed(restaurant: Restaurant) -> None:
    """Format detailed restaurant information."""
    google_indicator = " 🌐" if restaurant.google_place_id else ""
    expense_count = len(restaurant.expenses) if restaurant.expenses else 0

    click.echo(f"   📍 {restaurant.name}{google_indicator}")
    click.echo(f"      ID: {restaurant.id}")

    if restaurant.cuisine:
        click.echo(f"      Cuisine: {restaurant.cuisine}")
    if restaurant.address:
        click.echo(f"      Address: {restaurant.address}")
    if restaurant.city:
        location_parts = [restaurant.city]
        if restaurant.state:
            location_parts.append(restaurant.state)
        if restaurant.postal_code:
            location_parts.append(restaurant.postal_code)
        click.echo(f"      Location: {', '.join(location_parts)}")
    if restaurant.phone:
        click.echo(f"      Phone: {restaurant.phone}")
    if restaurant.google_place_id:
        click.echo(f"      Google Place ID: {restaurant.google_place_id}")

    click.echo(f"      Expenses: {expense_count}")

    if restaurant.rating:
        click.echo(f"      Rating: {restaurant.rating}/5.0")
    click.echo()


def _format_restaurant_simple(restaurant: Restaurant) -> None:
    """Format simple restaurant information."""
    google_indicator = " 🌐" if restaurant.google_place_id else ""
    expense_count = len(restaurant.expenses) if restaurant.expenses else 0
    click.echo(f"   - {restaurant.name}{google_indicator} ({expense_count} expenses)")


def _display_user_restaurants(user: User, restaurants: list[Restaurant], detailed: bool, with_google_id: bool) -> int:
    """Display restaurants for a single user and return Google ID count."""
    google_id_count = len([r for r in restaurants if r.google_place_id])

    click.echo(f"👤 {user.username} (ID: {user.id}) - {len(restaurants)} restaurants:")
    if with_google_id:
        click.echo("   (Filtered to show only restaurants with Google Place IDs)")

    if restaurants:
        for restaurant in restaurants:
            if detailed:
                _format_restaurant_detailed(restaurant)
            else:
                _format_restaurant_simple(restaurant)
    else:
        click.echo("   (No restaurants)")
    click.echo()

    return google_id_count


def _display_summary(total_restaurants: int, restaurants_with_google_id: int) -> None:
    """Display summary statistics."""
    click.echo("📊 Summary:")
    click.echo(f"   Total restaurants: {total_restaurants}")
    click.echo(f"   With Google Place ID: {restaurants_with_google_id}")
    click.echo(f"   Without Google Place ID: {total_restaurants - restaurants_with_google_id}")


@click.command("list")
@click.option("--user-id", type=int, help="Specific user ID to show restaurants for")
@click.option("--username", type=str, help="Specific username to show restaurants for")
@click.option("--all-users", is_flag=True, help="Show restaurants for all users")
@click.option("--detailed", is_flag=True, help="Show detailed restaurant information")
@click.option("--with-google-id", is_flag=True, help="Only show restaurants with Google Place IDs")
@with_appcontext
def list_restaurants(
    user_id: int | None, username: str | None, all_users: bool, detailed: bool, with_google_id: bool
) -> None:
    """List restaurants for users.

    Examples:
        flask restaurant list --user-id 1
        flask restaurant list --username admin
        flask restaurant list --all-users
        flask restaurant list --all-users --detailed
        flask restaurant list --username admin --with-google-id
    """
    if not any([user_id, username, all_users]):
        click.echo("❌ Error: Must specify --user-id, --username, or --all-users")
        return

    # Get target users
    users = _get_target_users(user_id, username, all_users)
    if not users:
        return

    click.echo(f"🍽️  Restaurants for {len(users)} user(s):\n")

    total_restaurants = 0
    restaurants_with_google_id = 0

    for user in users:
        restaurants = _get_user_restaurants(user, with_google_id)
        total_restaurants += len(restaurants)

        google_id_count = _display_user_restaurants(user, restaurants, detailed, with_google_id)
        restaurants_with_google_id += google_id_count

    # Summary
    if all_users:
        _display_summary(total_restaurants, restaurants_with_google_id)


def _get_restaurants_to_validate(
    user_id: int | None, username: str | None, all_users: bool, restaurant_id: int | None
) -> list[Restaurant]:
    """Get list of restaurants to validate based on options."""
    if restaurant_id:
        # Validate specific restaurant
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            click.echo(f"❌ Error: Restaurant with ID {restaurant_id} not found")
            return []
        click.echo(f"🔍 Validating restaurant: {restaurant.name} (ID: {restaurant.id})")
        return [restaurant]
    else:
        # Validate by user
        if not any([user_id, username, all_users]):
            click.echo("❌ Error: Must specify --user-id, --username, --all-users, or --restaurant-id")
            return []

        users = _get_target_users(user_id, username, all_users)
        if not users:
            return []

        restaurants_to_validate = []
        for user in users:
            user_restaurants = (
                Restaurant.query.filter_by(user_id=user.id).filter(Restaurant.google_place_id.isnot(None)).all()
            )
            restaurants_to_validate.extend(user_restaurants)

        click.echo(f"🔍 Validating {len(restaurants_to_validate)} restaurants with Google Place IDs...")
        return restaurants_to_validate


def _check_restaurant_mismatches(restaurant: Restaurant, validation_result: dict) -> tuple[list[str], dict[str, str]]:
    """Check for mismatches between restaurant data and Google data."""
    google_name = validation_result.get("google_name")
    google_street_address = validation_result.get("google_street_address")

    mismatches = []
    fixes_to_apply = {}

    if google_name and google_name.lower() != restaurant.name.lower():
        mismatches.append(f"Name: '{restaurant.name}' vs Google: '{google_name}'")
        fixes_to_apply["name"] = google_name

    if google_street_address and restaurant.address and google_street_address.lower() != restaurant.address.lower():
        mismatches.append(f"Address: '{restaurant.address}' vs Google: '{google_street_address}'")
        fixes_to_apply["address"] = google_street_address

    return mismatches, fixes_to_apply


def _apply_restaurant_fixes(restaurant: Restaurant, fixes_to_apply: dict[str, str], dry_run: bool) -> bool:
    """Apply fixes to restaurant data and return success status."""
    if dry_run:
        click.echo(f"   🔧 Would fix: {', '.join(fixes_to_apply.keys())}")
        return True
    else:
        try:
            # Apply fixes
            if "name" in fixes_to_apply:
                restaurant.name = fixes_to_apply["name"]
            if "street_address" in fixes_to_apply:
                restaurant.address = fixes_to_apply["address"]

            db.session.commit()
            click.echo(f"   ✅ Fixed: {', '.join(fixes_to_apply.keys())}")
            return True
        except Exception as e:
            db.session.rollback()
            click.echo(f"   ❌ Error fixing: {e}")
            return False


def _display_google_info(validation_result: dict) -> None:
    """Display additional Google Places information."""
    if validation_result.get("google_status"):
        click.echo(f"   📊 Status: {validation_result['google_status']}")
    if validation_result.get("google_rating"):
        click.echo(f"   ⭐ Google Rating: {validation_result['google_rating']}/5.0")
    if validation_result.get("google_phone"):
        click.echo(f"   📞 Phone: {validation_result['google_phone']}")
    if validation_result.get("google_website"):
        click.echo(f"   🌐 Website: {validation_result['google_website']}")
    if validation_result.get("google_price_level"):
        price_level = validation_result["google_price_level"]
        price_symbols = "💰" * price_level if isinstance(price_level, int) else price_level
        click.echo(f"   💲 Price Level: {price_symbols}")
    if validation_result.get("types"):
        # Handle both list and single value
        types_data = validation_result["types"]
        if isinstance(types_data, list):
            types_str = ", ".join(types_data[:3])  # Show first 3 types
        else:
            types_str = str(types_data)
        click.echo(f"   🏷️  Types: {types_str}")


def _process_restaurant_validation(restaurant: Restaurant, fix_mismatches: bool, dry_run: bool) -> tuple[str, bool]:
    """Process validation for a single restaurant and return status and fix success."""
    click.echo(f"\n🍽️  {restaurant.name} (ID: {restaurant.id})")
    click.echo(f"   User: {restaurant.user.username}")
    click.echo(f"   Google Place ID: {restaurant.google_place_id}")
    click.echo(f"   Full Address: {restaurant.full_address}")

    validation_result = _validate_restaurant_with_google(restaurant)

    if validation_result["valid"] is True:
        click.echo("   ✅ Valid")

        # Check for mismatches
        mismatches, fixes_to_apply = _check_restaurant_mismatches(restaurant, validation_result)

        if mismatches:
            click.echo("   ⚠️  Mismatches found:")
            for mismatch in mismatches:
                click.echo(f"      - {mismatch}")

            fixed = False
            if fix_mismatches and fixes_to_apply:
                fixed = _apply_restaurant_fixes(restaurant, fixes_to_apply, dry_run)

            _display_google_info(validation_result)
            return "valid", fixed
        else:
            _display_google_info(validation_result)
            return "valid", False

    elif validation_result["valid"] is False:
        click.echo("   ❌ Invalid")
        for error in validation_result["errors"]:
            click.echo(f"      Error: {error}")
        return "invalid", False
    else:
        click.echo("   ⚠️  Cannot validate")
        for error in validation_result["errors"]:
            click.echo(f"      Warning: {error}")
        return "error", False


def _display_validation_summary(
    valid_count: int, invalid_count: int, error_count: int, fixed_count: int, fix_mismatches: bool, dry_run: bool
) -> None:
    """Display validation summary."""
    click.echo("\n📊 Validation Summary:")
    click.echo(f"   ✅ Valid: {valid_count}")
    click.echo(f"   ❌ Invalid: {invalid_count}")
    click.echo(f"   ⚠️  Cannot validate: {error_count}")
    if fix_mismatches:
        if dry_run:
            click.echo(f"   🔧 Would fix: {fixed_count} restaurants")
        else:
            click.echo(f"   🔧 Fixed: {fixed_count} restaurants")


@click.command("validate")
@click.option("--user-id", type=int, help="Specific user ID to validate restaurants for")
@click.option("--username", type=str, help="Specific username to validate restaurants for")
@click.option("--all-users", is_flag=True, help="Validate restaurants for all users")
@click.option("--restaurant-id", type=int, help="Validate a specific restaurant by ID")
@click.option("--fix-mismatches", is_flag=True, help="Automatically fix name/address mismatches from Google")
@click.option("--dry-run", is_flag=True, help="Show what would be fixed without making changes")
@with_appcontext
def validate_restaurants(
    user_id: int | None,
    username: str | None,
    all_users: bool,
    restaurant_id: int | None,
    fix_mismatches: bool,
    dry_run: bool,
) -> None:
    """Validate restaurant information using Google Places API.

    This command checks restaurant data against Google Places API to verify:
    - Restaurant name accuracy
    - Address correctness
    - Business status (open/closed)
    - Additional metadata

    Examples:
        flask restaurant validate --user-id 1
        flask restaurant validate --username admin --dry-run
        flask restaurant validate --all-users
        flask restaurant validate --restaurant-id 123
        flask restaurant validate --username admin --fix-mismatches
    """
    restaurants_to_validate = _get_restaurants_to_validate(user_id, username, all_users, restaurant_id)

    if not restaurants_to_validate:
        click.echo("⚠️  No restaurants with Google Place IDs found to validate")
        return

    if dry_run and fix_mismatches:
        click.echo("🔍 DRY RUN MODE - No changes will be made\n")

    valid_count = 0
    invalid_count = 0
    error_count = 0
    fixed_count = 0

    for restaurant in restaurants_to_validate:
        status, fixed = _process_restaurant_validation(restaurant, fix_mismatches, dry_run)

        if status == "valid":
            valid_count += 1
        elif status == "invalid":
            invalid_count += 1
        else:
            error_count += 1

        if fixed:
            fixed_count += 1

    _display_validation_summary(valid_count, invalid_count, error_count, fixed_count, fix_mismatches, dry_run)
