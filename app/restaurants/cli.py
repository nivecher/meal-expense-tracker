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


def _build_street_address_from_components(address_components: list[dict]) -> str:
    """Build street address from Google Places address components."""
    street_number = next(
        (comp.get("long_name") for comp in address_components if "street_number" in comp.get("types", [])),
        None,
    )
    route = next(
        (comp.get("long_name") for comp in address_components if "route" in comp.get("types", [])),
        None,
    )
    return " ".join(filter(None, [street_number, route]))


def _detect_service_level_from_google_data(google_data: dict) -> tuple[str, float]:
    """Detect service level from Google Places data."""
    from app.restaurants.services import detect_service_level_from_google_data

    return detect_service_level_from_google_data(google_data)


def _get_restaurants_without_google_id(
    user_id: int | None, username: str | None, all_users: bool, restaurant_id: int | None
) -> list[Restaurant]:
    """Get restaurants without Google Place IDs for service level updates."""
    try:
        if restaurant_id:
            restaurant = Restaurant.query.get(restaurant_id)
            if restaurant and not restaurant.google_place_id:
                return [restaurant]
            return []

        users = _get_target_users(user_id, username, all_users)
        if not users:
            return []

        restaurants = []
        for user in users:
            user_restaurants = (
                Restaurant.query.filter_by(user_id=user.id).filter(Restaurant.google_place_id.is_(None)).all()
            )
            restaurants.extend(user_restaurants)

        return restaurants
    except Exception as e:
        click.echo(f"❌ Error getting restaurants without Google Place IDs: {e}")
        return []


def _update_service_levels_for_restaurants(restaurants: list[Restaurant], dry_run: bool) -> int:
    """Update service levels for restaurants using backend logic."""

    fixed_count = 0

    for restaurant in restaurants:
        click.echo(f"\n🍽️  {restaurant.name} (ID: {restaurant.id})")
        click.echo(f"   User: {restaurant.user.username}")
        click.echo(f"   Current Service Level: {restaurant.service_level or 'Not set'}")

        # Note: Google Places data not available without Google Place ID

        # For now, we'll use a simple heuristic based on restaurant name and other available data
        # This could be enhanced with external APIs or manual classification
        suggested_service_level = _suggest_service_level_from_restaurant_data(restaurant)

        if suggested_service_level and suggested_service_level != restaurant.service_level:
            if dry_run:
                click.echo(
                    f"   🔧 Would update service level: '{restaurant.service_level or 'Not set'}' → '{suggested_service_level}'"
                )
            else:
                try:
                    restaurant.service_level = suggested_service_level
                    db.session.commit()
                    click.echo(f"   ✅ Updated service level: '{suggested_service_level}'")
                    fixed_count += 1
                except Exception as e:
                    db.session.rollback()
                    click.echo(f"   ❌ Error updating service level: {e}")
        else:
            click.echo("   ℹ️  No service level update needed")

    return fixed_count


def _suggest_service_level_from_restaurant_data(restaurant: Restaurant) -> str | None:
    """Suggest service level using centralized detection logic."""
    from app.utils.service_level_detector import detect_service_level_from_name

    detected_level = detect_service_level_from_name(restaurant.name)
    return detected_level.value


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
                    "address_component",
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
                    "google_address_components": google_data.get("address_component", []),
                    "google_street_number": next(
                        (
                            comp.get("long_name")
                            for comp in google_data.get("address_component", [])
                            if "street_number" in comp.get("types", [])
                        ),
                        None,
                    ),
                    "google_route": next(
                        (
                            comp.get("long_name")
                            for comp in google_data.get("address_component", [])
                            if "route" in comp.get("types", [])
                        ),
                        None,
                    ),
                    "google_street_address": _build_street_address_from_components(
                        google_data.get("address_component", [])
                    ),
                    "google_service_level": _detect_service_level_from_google_data(google_data),
                    "google_city": next(
                        (
                            comp.get("long_name")
                            for comp in google_data.get("address_component", [])
                            if "locality" in comp.get("types", [])
                        ),
                        None,
                    ),
                    "google_state": next(
                        (
                            comp.get("short_name")
                            for comp in google_data.get("address_component", [])
                            if "administrative_area_level_1" in comp.get("types", [])
                        ),
                        None,
                    ),
                    "google_postal_code": next(
                        (
                            comp.get("long_name")
                            for comp in google_data.get("address_component", [])
                            if "postal_code" in comp.get("types", [])
                        ),
                        None,
                    ),
                    "google_country": next(
                        (
                            comp.get("long_name")
                            for comp in google_data.get("address_component", [])
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
) -> tuple[list[Restaurant], dict[str, int]]:
    """Get list of restaurants to validate based on options."""
    counts = {"total_restaurants": 0, "missing_google_id": 0, "with_google_id": 0}

    if restaurant_id:
        # Validate specific restaurant
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            click.echo(f"❌ Error: Restaurant with ID {restaurant_id} not found")
            return [], counts

        counts["total_restaurants"] = 1
        if restaurant.google_place_id:
            counts["with_google_id"] = 1
        else:
            counts["missing_google_id"] = 1

        click.echo(f"🔍 Validating restaurant: {restaurant.name} (ID: {restaurant.id})")
        return [restaurant] if restaurant.google_place_id else [], counts
    else:
        # Validate by user
        if not any([user_id, username, all_users]):
            click.echo("❌ Error: Must specify --user-id, --username, --all-users, or --restaurant-id")
            return [], counts

        users = _get_target_users(user_id, username, all_users)
        if not users:
            return [], counts

        restaurants_to_validate = []
        for user in users:
            # Get all restaurants for count statistics
            all_user_restaurants = Restaurant.query.filter_by(user_id=user.id).all()
            counts["total_restaurants"] += len(all_user_restaurants)

            # Get restaurants with Google Place IDs for validation
            user_restaurants_with_google_id = [r for r in all_user_restaurants if r.google_place_id]
            user_restaurants_without_google_id = [r for r in all_user_restaurants if not r.google_place_id]

            counts["with_google_id"] += len(user_restaurants_with_google_id)
            counts["missing_google_id"] += len(user_restaurants_without_google_id)

            restaurants_to_validate.extend(user_restaurants_with_google_id)

        click.echo(f"🔍 Validating {len(restaurants_to_validate)} restaurants with Google Place IDs...")
        return restaurants_to_validate, counts


def _check_restaurant_mismatches(restaurant: Restaurant, validation_result: dict) -> tuple[list[str], dict[str, str]]:
    """Check for mismatches between restaurant data and Google data."""
    google_name = validation_result.get("google_name")
    google_street_address = validation_result.get("google_street_address")
    google_service_level_data = validation_result.get("google_service_level")

    mismatches = []
    fixes_to_apply = {}

    if google_name and google_name.lower() != restaurant.name.lower():
        mismatches.append(f"Name: '{restaurant.name}' vs Google: '{google_name}'")
        fixes_to_apply["name"] = google_name

    if google_street_address and restaurant.address and google_street_address.lower() != restaurant.address.lower():
        mismatches.append(f"Address: '{restaurant.address}' vs Google: '{google_street_address}'")
        fixes_to_apply["address"] = google_street_address

    # Check service level
    if google_service_level_data:
        google_service_level, confidence = google_service_level_data
        from app.restaurants.services import validate_restaurant_service_level

        has_mismatch, mismatch_message, suggested_fix = validate_restaurant_service_level(
            restaurant, google_service_level, confidence
        )

        if has_mismatch:
            mismatches.append(mismatch_message)
            if suggested_fix:
                fixes_to_apply["service_level"] = suggested_fix

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
            if "address" in fixes_to_apply:
                restaurant.address = fixes_to_apply["address"]
            if "service_level" in fixes_to_apply:
                restaurant.service_level = fixes_to_apply["service_level"]

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
    if validation_result.get("google_service_level"):
        service_level, confidence = validation_result["google_service_level"]
        if service_level != "unknown":
            from app.restaurants.services import get_service_level_display_info

            display_info = get_service_level_display_info(service_level)
            click.echo(f"   🍽️  Service Level: {display_info['display_name']} (confidence: {confidence:.2f})")


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


def _handle_service_level_updates(
    user_id: int | None,
    username: str | None,
    all_users: bool,
    restaurant_id: int | None,
    update_service_levels: bool,
    dry_run: bool,
) -> tuple[int, int]:
    """Handle service level updates for restaurants without Google Place IDs.

    Returns:
        Tuple of (updated_count, total_count)
    """
    if not update_service_levels:
        return 0, 0

    restaurants_without_google_id = _get_restaurants_without_google_id(user_id, username, all_users, restaurant_id)
    if restaurants_without_google_id:
        click.echo(
            f"🔄 Updating service levels for {len(restaurants_without_google_id)} restaurants without Google Place IDs..."
        )
        service_level_fixed_count = _update_service_levels_for_restaurants(restaurants_without_google_id, dry_run)
        click.echo(f"✅ Updated service levels for {service_level_fixed_count} restaurants")
        return service_level_fixed_count, len(restaurants_without_google_id)
    else:
        click.echo("ℹ️  No restaurants without Google Place IDs found for service level updates")
        return 0, 0


def _handle_restaurant_validation(
    restaurants_to_validate: list[Restaurant],
    restaurant_counts: dict[str, int],
    fix_mismatches: bool,
    dry_run: bool,
    service_level_updated_count: int = 0,
    service_level_total_count: int = 0,
) -> None:
    """Handle restaurant validation with Google Places API."""
    if not restaurants_to_validate:
        click.echo("⚠️  No restaurants with Google Place IDs found to validate")
        # Still show summary even when no restaurants to validate
        _display_validation_summary(
            0,
            0,
            0,
            0,
            0,
            restaurant_counts["total_restaurants"],
            restaurant_counts["missing_google_id"],
            restaurant_counts["with_google_id"],
            fix_mismatches,
            dry_run,
            service_level_updated_count,
            service_level_total_count,
        )
        return

    if dry_run and fix_mismatches:
        click.echo("🔍 DRY RUN MODE - No changes will be made\n")

    valid_count = 0
    invalid_count = 0
    error_count = 0
    fixed_count = 0
    mismatch_count = 0

    for restaurant in restaurants_to_validate:
        status, fixed = _process_restaurant_validation(restaurant, fix_mismatches, dry_run)

        if status == "valid":
            valid_count += 1

            # Check for mismatches
            validation_result = _validate_restaurant_with_google(restaurant)
            if validation_result["valid"] is True:
                mismatches, _ = _check_restaurant_mismatches(restaurant, validation_result)
                if mismatches:
                    mismatch_count += 1

        elif status == "invalid":
            invalid_count += 1
        else:
            error_count += 1

        if fixed:
            fixed_count += 1

    _display_validation_summary(
        valid_count,
        invalid_count,
        error_count,
        fixed_count,
        mismatch_count,
        restaurant_counts["total_restaurants"],
        restaurant_counts["missing_google_id"],
        restaurant_counts["with_google_id"],
        fix_mismatches,
        dry_run,
        service_level_updated_count,
        service_level_total_count,
    )


def _display_validation_summary(
    valid_count: int,
    invalid_count: int,
    error_count: int,
    fixed_count: int,
    mismatch_count: int,
    total_restaurants: int,
    missing_google_id: int,
    with_google_id: int,
    fix_mismatches: bool,
    dry_run: bool,
    service_level_updated_count: int = 0,
    service_level_total_count: int = 0,
) -> None:
    """Display validation summary."""
    click.echo("\n📊 Validation Summary:")

    # Restaurant counts
    click.echo(f"   🍽️  Total restaurants: {total_restaurants}")
    click.echo(f"   🌐 With Google Place ID: {with_google_id}")
    click.echo(f"   📍 Missing Google Place ID: {missing_google_id}")

    # Validation results
    click.echo(f"   ✅ Valid: {valid_count}")
    click.echo(f"   ❌ Invalid: {invalid_count}")
    click.echo(f"   ⚠️  Cannot validate: {error_count}")

    # Mismatch count
    if mismatch_count > 0:
        click.echo(f"   🔄 With mismatches: {mismatch_count}")

    # Fixed count
    if fix_mismatches:
        if dry_run:
            click.echo(f"   🔧 Would fix: {fixed_count} restaurants")
        else:
            click.echo(f"   🔧 Fixed: {fixed_count} restaurants")

    # Service level metrics
    if service_level_total_count > 0:
        click.echo("   🍽️  Service Level Updates:")
        click.echo(f"      📊 Total without Google Place ID: {service_level_total_count}")
        if dry_run:
            click.echo(f"      🔧 Would update: {service_level_updated_count} restaurants")
        else:
            click.echo(f"      ✅ Updated: {service_level_updated_count} restaurants")


@click.command("validate")
@click.option("--user-id", type=int, help="Specific user ID to validate restaurants for")
@click.option("--username", type=str, help="Specific username to validate restaurants for")
@click.option("--all-users", is_flag=True, help="Validate restaurants for all users")
@click.option("--restaurant-id", type=int, help="Validate a specific restaurant by ID")
@click.option("--fix-mismatches", is_flag=True, help="Automatically fix name/address mismatches from Google")
@click.option(
    "--update-service-levels", is_flag=True, help="Update service levels for restaurants without Google Place IDs"
)
@click.option("--dry-run", is_flag=True, help="Show what would be fixed without making changes")
@with_appcontext
def validate_restaurants(
    user_id: int | None,
    username: str | None,
    all_users: bool,
    restaurant_id: int | None,
    fix_mismatches: bool,
    update_service_levels: bool,
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
    restaurants_to_validate, restaurant_counts = _get_restaurants_to_validate(
        user_id, username, all_users, restaurant_id
    )

    # Handle service level updates
    service_level_updated_count, service_level_total_count = _handle_service_level_updates(
        user_id, username, all_users, restaurant_id, update_service_levels, dry_run
    )

    # Handle restaurant validation
    _handle_restaurant_validation(
        restaurants_to_validate,
        restaurant_counts,
        fix_mismatches,
        dry_run,
        service_level_updated_count,
        service_level_total_count,
    )
