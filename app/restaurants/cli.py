"""CLI commands for restaurant management."""

from __future__ import annotations

import math

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


def _search_google_places_by_name_and_address(name: str, address: str | None = None) -> list[dict]:
    """Search Google Places API for restaurants by name and address."""
    try:
        from app.services.google_places_service import get_google_places_service

        places_service = get_google_places_service()

        # Build search query
        search_query = name
        if address:
            search_query += f" {address}"

        # Search for places
        places = places_service.search_places_by_text(search_query, max_results=10)

        return places

    except Exception as e:
        click.echo(f"❌ Error searching Google Places: {e}")
        return []


def _find_google_place_match(restaurant: Restaurant) -> tuple[str | None, list[dict]]:
    """Find Google Place ID match for a restaurant based on name and address."""
    # Build search query from restaurant data
    name = restaurant.name
    address = restaurant.full_address

    # Search for matches
    places = _search_google_places_by_name_and_address(name, address)

    if not places:
        return None, []

    # Check for exact matches
    exact_matches = []
    for place in places:
        place_name = (
            place.get("displayName", {}).get("text", "")
            if isinstance(place.get("displayName"), dict)
            else place.get("displayName", "")
        )

        # Check if names match (case-insensitive)
        if place_name.lower() == name.lower():
            exact_matches.append(place)

    # If only one exact match, return it
    if len(exact_matches) == 1:
        return exact_matches[0].get("id"), exact_matches

    # If multiple exact matches, return all for user to choose
    if len(exact_matches) > 1:
        return None, exact_matches

    # If no exact matches, return all results for user to choose
    return None, places


def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates using Haversine formula.

    Args:
        lat1, lon1: First coordinate (latitude, longitude)
        lat2, lon2: Second coordinate (latitude, longitude)

    Returns:
        Distance in miles
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    # Earth's radius in miles
    earth_radius_miles = 3959
    return earth_radius_miles * c


def _find_closest_match(restaurant: Restaurant, matches: list[dict]) -> dict | None:
    """Find the closest match based on restaurant address and Google Places coordinates."""
    if not matches:
        return None

    # For now, we'll use a simple approach: if the restaurant has city/state info,
    # we'll prefer matches that contain those in their address
    restaurant_city = restaurant.city
    restaurant_state = restaurant.state

    if not restaurant_city or not restaurant_state:
        # If no city/state info, return first match
        return matches[0]

    # Score matches based on address similarity
    best_match = None
    best_score = -1

    for match in matches:
        match_address = match.get("formattedAddress", "").lower()
        score = 0

        # Check for city match
        if restaurant_city.lower() in match_address:
            score += 2

        # Check for state match
        if restaurant_state.lower() in match_address:
            score += 1

        # Check for exact city, state combination
        city_state_combo = f"{restaurant_city.lower()}, {restaurant_state.lower()}"
        if city_state_combo in match_address:
            score += 3

        if score > best_score:
            best_score = score
            best_match = match

    # Return best match or first match if no scoring worked
    return best_match if best_match else matches[0]


def _get_restaurants_without_google_id(
    user_id: int | None, username: str | None, all_users: bool, restaurant_id: int | None
) -> list[Restaurant]:
    """Get restaurants without Google Place IDs for service level updates."""
    try:
        if restaurant_id:
            from app.extensions import db

            restaurant = db.session.get(Restaurant, restaurant_id)
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
        users = User.query.all()
        if not users:
            click.echo("❌ Error: No users found in database")
            return []
        return users
    return []


def _validate_restaurant_with_google(restaurant: Restaurant) -> dict:
    """Validate restaurant information using new Google Places API service.

    Args:
        restaurant: Restaurant instance to validate

    Returns:
        Dictionary with validation results
    """
    try:
        from app.services.google_places_service import get_google_places_service

        if restaurant.google_place_id:
            try:
                places_service = get_google_places_service()
            except ValueError as e:
                if "API key" in str(e):
                    return {
                        "valid": False,
                        "errors": ["Google Places API key not configured - cannot validate"],
                    }
                raise

            place_data = places_service.get_place_details(restaurant.google_place_id)

            if not place_data:
                return {
                    "valid": False,
                    "errors": ["Failed to retrieve place data from Google Places API"],
                }

            # Extract restaurant data using the service
            google_data = places_service.extract_restaurant_data(place_data)

            return {
                "valid": True,
                "google_name": google_data.get("name"),
                "google_address": google_data.get("formatted_address"),
                "google_rating": google_data.get("rating"),
                "google_status": google_data.get("business_status", "OPERATIONAL"),
                "types": google_data.get("types", []),
                "primary_type": google_data.get("primary_type"),
                "google_phone": google_data.get("phone_number"),
                "google_website": google_data.get("website"),
                "google_price_level": google_data.get("price_level"),
                "google_address_line_1": google_data.get("address_line_1"),
                "google_address_line_2": google_data.get("address_line_2"),
                "google_city": google_data.get("city"),
                "google_state": google_data.get("state"),
                "google_state_long": google_data.get("state_long"),
                "google_state_short": google_data.get("state_short"),
                "google_postal_code": google_data.get("postal_code"),
                "google_country": google_data.get("country"),
                "google_service_level": {
                    "level": places_service.detect_service_level_from_data(place_data)[0],
                    "confidence": places_service.detect_service_level_from_data(place_data)[1],
                },
                "google_cuisine": places_service.analyze_restaurant_types(place_data).get("cuisine_type"),
                "errors": [],
            }
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

    _display_restaurant_basic_info(restaurant)
    _display_restaurant_address_info(restaurant)
    _display_restaurant_contact_info(restaurant)

    click.echo(f"      Expenses: {expense_count}")
    if restaurant.rating:
        click.echo(f"      Rating: {restaurant.rating}/5.0")
    click.echo()


def _display_restaurant_basic_info(restaurant: Restaurant) -> None:
    """Display basic restaurant information."""
    if restaurant.cuisine:
        click.echo(f"      Cuisine: {restaurant.cuisine}")


def _display_restaurant_address_info(restaurant: Restaurant) -> None:
    """Display restaurant address information."""
    # Display address information
    address_parts = []
    if restaurant.address_line_1:
        address_parts.append(restaurant.address_line_1)
    if restaurant.address_line_2:
        address_parts.append(restaurant.address_line_2)
    if address_parts:
        click.echo(f"      Address: {', '.join(address_parts)}")

    # Display location information
    if restaurant.city:
        location_parts = [restaurant.city]
        if restaurant.state:
            location_parts.append(restaurant.state)
        if restaurant.postal_code:
            location_parts.append(restaurant.postal_code)
        if restaurant.country:
            location_parts.append(restaurant.country)
        click.echo(f"      Location: {', '.join(location_parts)}")


def _display_restaurant_contact_info(restaurant: Restaurant) -> None:
    """Display restaurant contact information."""
    if restaurant.phone:
        click.echo(f"      Phone: {restaurant.phone}")
    if restaurant.google_place_id:
        click.echo(f"      Google Place ID: {restaurant.google_place_id}")


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
        from app.extensions import db

        restaurant = db.session.get(Restaurant, restaurant_id)
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
    mismatches = []
    fixes_to_apply = {}

    # Check name mismatch
    _check_name_mismatch(restaurant, validation_result, mismatches, fixes_to_apply)

    # Check address mismatches
    _check_address_mismatches(restaurant, validation_result, mismatches, fixes_to_apply)

    # Check service level mismatch
    _check_service_level_mismatch(restaurant, validation_result, mismatches, fixes_to_apply)

    # Check price level mismatch
    _check_price_level_mismatch(restaurant, validation_result, mismatches, fixes_to_apply)

    # Check cuisine mismatch
    _check_cuisine_mismatch(restaurant, validation_result, mismatches, fixes_to_apply)

    # Check phone mismatch
    _check_phone_mismatch(restaurant, validation_result, mismatches, fixes_to_apply)

    # Check website mismatch
    _check_website_mismatch(restaurant, validation_result, mismatches, fixes_to_apply)

    # Check type mismatch
    _check_type_mismatch(restaurant, validation_result, mismatches, fixes_to_apply)

    return mismatches, fixes_to_apply


def _check_name_mismatch(
    restaurant: Restaurant, validation_result: dict, mismatches: list, fixes_to_apply: dict
) -> None:
    """Check for name mismatches."""
    google_name = validation_result.get("google_name")
    if google_name and google_name.lower() != restaurant.name.lower():
        mismatches.append(f"Name: '{restaurant.name}' vs Google: '{google_name}'")
        fixes_to_apply["name"] = google_name


def _check_address_mismatches(
    restaurant: Restaurant, validation_result: dict, mismatches: list, fixes_to_apply: dict
) -> None:
    """Check for address component mismatches."""
    address_checks = [
        ("google_address_line_1", "address_line_1", "Address Line 1"),
        ("google_address_line_2", "address_line_2", "Address Line 2"),
        ("google_city", "city", "City"),
        ("google_postal_code", "postal_code", "Postal Code"),
        ("google_country", "country", "Country"),
    ]

    # Handle regular address fields with simple string comparison
    for google_field, restaurant_field, display_name in address_checks:
        google_value = validation_result.get(google_field)
        restaurant_value = getattr(restaurant, restaurant_field)

        if google_value and restaurant_value and google_value.lower() != restaurant_value.lower():
            mismatches.append(f"{display_name}: '{restaurant_value}' vs Google: '{google_value}'")
            fixes_to_apply[restaurant_field] = google_value

    # Handle state field with specialized matching
    current_data = {
        "state": restaurant.state,
        "country": restaurant.country,
    }
    _check_state_mismatch(current_data, validation_result, mismatches, fixes_to_apply)


def _check_state_mismatch(current_data: dict, validation_result: dict, mismatches: list, fixes_to_apply: dict) -> None:
    """Check for state field mismatches using multiple comparison methods."""

    google_state = validation_result.get("google_state")
    google_state_long = validation_result.get("google_state_long")
    google_state_short = validation_result.get("google_state_short")
    current_state = current_data.get("state")

    if not ((google_state or google_state_long or google_state_short) and current_state):
        return

    # Check direct string matches first
    if _states_match_directly(current_state, google_state, google_state_long, google_state_short):
        return

    # Try US library matching as fallback
    if _states_match_with_us_library(current_state, google_state, google_state_long, google_state_short):
        return

    # No matches found - report mismatch
    # Use long version for display if available, otherwise fall back to regular state
    display_state = google_state_long or google_state
    mismatches.append(f"State: '{current_state}' vs Google: '{display_state}'")
    fixes_to_apply["state"] = google_state_long or google_state


def _states_match_directly(
    current_state: str, google_state: str, google_state_long: str, google_state_short: str
) -> bool:
    """Check if current state matches any Google state format directly."""
    current_state_lower = current_state.lower()

    if google_state and google_state.lower() == current_state_lower:
        return True
    if google_state_long and google_state_long.lower() == current_state_lower:
        return True
    if google_state_short and google_state_short.lower() == current_state_lower:
        return True

    return False


def _states_match_with_us_library(
    current_state: str, google_state: str, google_state_long: str, google_state_short: str
) -> bool:
    """Check if states match using US library normalization."""
    import us

    current_state_obj = us.states.lookup(current_state)
    if not current_state_obj:
        return False

    # Check each Google state format
    for google_state_value in [google_state, google_state_long, google_state_short]:
        if google_state_value:
            google_state_obj = us.states.lookup(google_state_value)
            if google_state_obj and current_state_obj.abbr == google_state_obj.abbr:
                return True

    return False


def _check_service_level_mismatch(
    restaurant: Restaurant, validation_result: dict, mismatches: list, fixes_to_apply: dict
) -> None:
    """Check for service level mismatches."""
    google_service_level_data = validation_result.get("google_service_level")

    if google_service_level_data:
        google_service_level, confidence = google_service_level_data
        from app.restaurants.services import validate_restaurant_service_level

        # Create current_data from restaurant for validation
        current_data = {
            "service_level": restaurant.service_level,
        }

        has_mismatch, mismatch_message, suggested_fix = validate_restaurant_service_level(
            current_data, google_service_level, confidence
        )

        if has_mismatch:
            mismatches.append(mismatch_message)
            if suggested_fix:
                fixes_to_apply["service_level"] = suggested_fix


def _check_price_level_mismatch(
    restaurant: Restaurant, validation_result: dict, mismatches: list, fixes_to_apply: dict
) -> None:
    """Check for price level mismatches."""
    google_price_level_raw = validation_result.get("google_price_level")

    if google_price_level_raw is not None:
        # Convert Google price level to integer for comparison
        from app.services.google_places_service import get_google_places_service

        places_service = get_google_places_service()
        google_price_level = places_service.convert_price_level_to_int(google_price_level_raw)
        restaurant_price_level = restaurant.price_level

        # Check for mismatch (including None vs non-None)
        if restaurant_price_level != google_price_level:
            restaurant_display = _format_price_level_display(restaurant_price_level)
            google_display = _format_price_level_display(google_price_level)

            mismatches.append(f"Price Level: '{restaurant_display}' vs Google: '{google_display}'")
            fixes_to_apply["price_level"] = google_price_level


def _format_price_level_display(price_level):
    """Format price level for display in mismatch messages."""
    if price_level is None:
        return "Not set"

    price_levels = {
        0: "Free",
        1: "$ (Inexpensive)",
        2: "$$ (Moderate)",
        3: "$$$ (Expensive)",
        4: "$$$$ (Very Expensive)",
    }
    return price_levels.get(price_level, str(price_level))


def _check_cuisine_mismatch(
    restaurant: Restaurant, validation_result: dict, mismatches: list, fixes_to_apply: dict
) -> None:
    """Check for cuisine mismatches."""
    google_cuisine = validation_result.get("google_cuisine")

    if google_cuisine is not None:
        restaurant_cuisine = restaurant.cuisine

        # Check for mismatch (including None vs non-None)
        if restaurant_cuisine != google_cuisine:
            restaurant_display = restaurant_cuisine or "Not set"
            google_display = google_cuisine or "Not set"

            mismatches.append(f"Cuisine: '{restaurant_display}' vs Google: '{google_display}'")
            fixes_to_apply["cuisine"] = google_cuisine


def _check_phone_mismatch(
    restaurant: Restaurant, validation_result: dict, mismatches: list, fixes_to_apply: dict
) -> None:
    """Check for phone mismatches."""
    google_phone = validation_result.get("google_phone")

    if google_phone is not None:
        restaurant_phone = restaurant.phone

        # Check for mismatch (including None vs non-None)
        if restaurant_phone != google_phone:
            restaurant_display = restaurant_phone or "Not set"
            google_display = google_phone or "Not set"

            mismatches.append(f"Phone: '{restaurant_display}' vs Google: '{google_display}'")
            fixes_to_apply["phone"] = google_phone


def _check_website_mismatch(
    restaurant: Restaurant, validation_result: dict, mismatches: list, fixes_to_apply: dict
) -> None:
    """Check for website mismatches."""
    google_website = validation_result.get("google_website")

    if google_website is not None:
        restaurant_website = restaurant.website

        # Check for mismatch (including None vs non-None)
        if restaurant_website != google_website:
            restaurant_display = restaurant_website or "Not set"
            google_display = google_website or "Not set"

            mismatches.append(f"Website: '{restaurant_display}' vs Google: '{google_display}'")
            fixes_to_apply["website"] = google_website


def _check_type_mismatch(
    restaurant: Restaurant, validation_result: dict, mismatches: list, fixes_to_apply: dict
) -> None:
    """Check for type mismatches."""
    google_primary_type = validation_result.get("primary_type")

    if google_primary_type is not None:
        restaurant_type = restaurant.type

        # Check for mismatch (including None vs non-None)
        if restaurant_type != google_primary_type:
            restaurant_display = restaurant_type or "Not set"
            google_display = google_primary_type or "Not set"

            mismatches.append(f"Type: '{restaurant_display}' vs Google: '{google_display}'")
            fixes_to_apply["type"] = google_primary_type


def _apply_restaurant_fixes(restaurant: Restaurant, fixes_to_apply: dict[str, str], dry_run: bool) -> bool:
    """Apply fixes to restaurant data and return success status."""
    if dry_run:
        click.echo(f"   🔧 Would fix: {', '.join(fixes_to_apply.keys())}")
        return True
    else:
        try:
            _apply_restaurant_field_fixes(restaurant, fixes_to_apply)
            db.session.commit()
            click.echo(f"   ✅ Fixed: {', '.join(fixes_to_apply.keys())}")
            return True
        except Exception as e:
            db.session.rollback()
            click.echo(f"   ❌ Error fixing: {e}")
            return False


def _apply_restaurant_field_fixes(restaurant: Restaurant, fixes_to_apply: dict[str, str]) -> None:
    """Apply field fixes to restaurant object."""
    field_mappings = {
        "name": "name",
        "address_line_1": "address_line_1",
        "address_line_2": "address_line_2",
        "city": "city",
        "state": "state",
        "postal_code": "postal_code",
        "country": "country",
        "service_level": "service_level",
        "price_level": "price_level",
        "cuisine": "cuisine",
        "phone": "phone",
        "website": "website",
        "type": "type",
    }

    for fix_key, field_name in field_mappings.items():
        if fix_key in fixes_to_apply:
            setattr(restaurant, field_name, fixes_to_apply[fix_key])


def _display_address_comparison(restaurant: Restaurant, validation_result: dict) -> None:
    """Display detailed address comparison between stored and Google data."""
    # Check if there are any address-related mismatches
    address_fields = ["address_line_1", "address_line_2", "city", "state", "postal_code", "country"]

    has_address_mismatch = False
    for field in address_fields:
        google_field = f"google_{field}"
        if google_field in validation_result and validation_result[google_field]:
            stored_value = getattr(restaurant, field)
            google_value = validation_result[google_field]
            if stored_value and google_value and stored_value.lower() != google_value.lower():
                has_address_mismatch = True
                break

    if has_address_mismatch:
        click.echo("   📍 Address Comparison:")
        click.echo("      Stored Address:")
        click.echo(f"         Street: {restaurant.address_line_1 or 'N/A'}")
        if restaurant.address_line_2:
            click.echo(f"         Unit: {restaurant.address_line_2}")
        click.echo(f"         City: {restaurant.city or 'N/A'}")
        click.echo(f"         State: {restaurant.state or 'N/A'}")
        click.echo(f"         ZIP: {restaurant.postal_code or 'N/A'}")
        click.echo(f"         Country: {restaurant.country or 'N/A'}")

        click.echo("      Google Address:")
        click.echo(f"         Street: {validation_result.get('google_address_line_1', 'N/A')}")
        if validation_result.get("google_address_line_2"):
            click.echo(f"         Unit: {validation_result['google_address_line_2']}")
        click.echo(f"         City: {validation_result.get('google_city', 'N/A')}")
        click.echo(f"         State: {validation_result.get('google_state', 'N/A')}")
        click.echo(f"         ZIP: {validation_result.get('google_postal_code', 'N/A')}")
        click.echo(f"         Country: {validation_result.get('google_country', 'N/A')}")


def _display_google_info(validation_result: dict) -> None:
    """Display additional Google Places information."""
    # Display Google's address information
    if validation_result.get("google_address"):
        click.echo(f"   🗺️  Google Address: {validation_result['google_address']}")

    _display_google_basic_info(validation_result)
    _display_google_service_info(validation_result)


def _display_google_basic_info(validation_result: dict) -> None:
    """Display basic Google Places information."""
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
        price_display = _format_price_level_display(price_level)
        click.echo(f"   💲 Price Level: {price_display}")
    if validation_result.get("types"):
        # Handle both list and single value
        types_data = validation_result["types"]
        if isinstance(types_data, list):
            types_str = ", ".join(types_data[:3])  # Show first 3 types
        else:
            types_str = str(types_data)
        click.echo(f"   🏷️  Types: {types_str}")


def _display_google_service_info(validation_result: dict) -> None:
    """Display Google service level information."""
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

            # Show detailed address comparison for address mismatches
            _display_address_comparison(restaurant, validation_result)

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
    place_id_found_count: int = 0,
    place_id_warning_count: int = 0,
    place_id_error_count: int = 0,
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
            place_id_found_count,
            place_id_warning_count,
            place_id_error_count,
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
        place_id_found_count,
        place_id_warning_count,
        place_id_error_count,
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
    place_id_found_count: int = 0,
    place_id_warning_count: int = 0,
    place_id_error_count: int = 0,
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

    # Place ID finding results
    if place_id_found_count > 0 or place_id_warning_count > 0 or place_id_error_count > 0:
        click.echo("\n🔍 Place ID Finding Results:")
        click.echo(f"   ✅ Found Place IDs: {place_id_found_count}")
        if place_id_warning_count > 0:
            click.echo(f"   ⚠️  Multiple matches (needs review): {place_id_warning_count}")
        if place_id_error_count > 0:
            click.echo(f"   ❌ No matches found: {place_id_error_count}")

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


def _process_restaurant_place_id_finding(restaurant: Restaurant, closest: bool, dry_run: bool) -> tuple[str, bool]:
    """Process place ID finding for a single restaurant and return status and success."""
    click.echo(f"\n🍽️  {restaurant.name} (ID: {restaurant.id})")
    click.echo(f"   User: {restaurant.user.username}")
    click.echo(f"   Address: {restaurant.full_address}")

    place_id, matches = _find_google_place_match(restaurant)

    if place_id:
        # Single exact match found
        click.echo(f"   ✅ Found exact match: {place_id}")
        if not dry_run:
            restaurant.google_place_id = place_id
            db.session.commit()
            click.echo("   💾 Updated restaurant with Google Place ID")
        else:
            click.echo("   🔧 Would update restaurant with Google Place ID")
        return "found", True
    elif matches:
        # Multiple matches or no exact match
        if closest and len(matches) > 1:
            # Find closest match
            closest_match = _find_closest_match(restaurant, matches)
            if closest_match:
                closest_place_id = closest_match.get("id")
                closest_name = (
                    closest_match.get("displayName", {}).get("text", "")
                    if isinstance(closest_match.get("displayName"), dict)
                    else closest_match.get("displayName", "")
                )
                closest_address = closest_match.get("formattedAddress", "")
                closest_rating = closest_match.get("rating", "N/A")

                click.echo(f"   🎯 Selected closest match from {len(matches)} options:")
                click.echo(f"      {closest_name} - {closest_address} (Rating: {closest_rating})")

                if not dry_run:
                    restaurant.google_place_id = closest_place_id
                    db.session.commit()
                    click.echo("   💾 Updated restaurant with closest Google Place ID")
                else:
                    click.echo("   🔧 Would update restaurant with closest Google Place ID")
                return "found", True
            else:
                click.echo(f"   ⚠️  Found {len(matches)} potential matches (could not determine closest):")
                _display_matches(matches)
                return "warning", False
        else:
            # Show all matches for manual review
            click.echo(f"   ⚠️  Found {len(matches)} potential matches:")
            _display_matches(matches)
            return "warning", False
    else:
        # No matches found
        click.echo("   ❌ No matches found")
        return "error", False


def _display_matches(matches: list[dict]) -> None:
    """Display match information for manual review."""
    for i, match in enumerate(matches[:5], 1):  # Show first 5 matches
        match_name = (
            match.get("displayName", {}).get("text", "")
            if isinstance(match.get("displayName"), dict)
            else match.get("displayName", "")
        )
        match_address = match.get("formattedAddress", "")
        match_rating = match.get("rating", "N/A")
        click.echo(f"      {i}. {match_name} - {match_address} (Rating: {match_rating})")


def _handle_place_id_finding(
    user_id: int | None,
    username: str | None,
    all_users: bool,
    restaurant_id: int | None,
    closest: bool,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Handle finding Google Place IDs for restaurants without them."""
    # Get restaurants without Google Place IDs
    restaurants_without_google_id = _get_restaurants_without_google_id(user_id, username, all_users, restaurant_id)

    if not restaurants_without_google_id:
        click.echo("✅ All restaurants already have Google Place IDs")
        return 0, 0, 0

    click.echo(f"\n🔍 Finding Google Place IDs for {len(restaurants_without_google_id)} restaurants...")
    if dry_run:
        click.echo("🔍 DRY RUN MODE - No changes will be made\n")

    found_count = 0
    warning_count = 0
    error_count = 0

    for restaurant in restaurants_without_google_id:
        status, success = _process_restaurant_place_id_finding(restaurant, closest, dry_run)

        if status == "found":
            found_count += 1
        elif status == "warning":
            warning_count += 1
        else:
            error_count += 1

    # Return statistics for integration into main summary
    return found_count, warning_count, error_count


@click.command("validate")
@click.option("--user-id", type=int, help="Specific user ID to validate restaurants for")
@click.option("--username", type=str, help="Specific username to validate restaurants for")
@click.option("--all-users", is_flag=True, help="Validate restaurants for all users")
@click.option("--restaurant-id", type=int, help="Validate a specific restaurant by ID")
@click.option("--fix-mismatches", is_flag=True, help="Automatically fix name/address mismatches from Google")
@click.option(
    "--update-service-levels",
    is_flag=True,
    help="Update service levels for restaurants without Google Place IDs",
)
@click.option("--find-place-id", is_flag=True, help="Find Google Place ID matches for restaurants without one")
@click.option(
    "--closest",
    is_flag=True,
    help="Automatically select closest match when multiple options are found",
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
    find_place_id: bool,
    closest: bool,
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
        flask restaurant validate --find-place-id --dry-run
        flask restaurant validate --find-place-id --closest --dry-run
    """
    restaurants_to_validate, restaurant_counts = _get_restaurants_to_validate(
        user_id, username, all_users, restaurant_id
    )

    # Handle service level updates
    service_level_updated_count, service_level_total_count = _handle_service_level_updates(
        user_id, username, all_users, restaurant_id, update_service_levels, dry_run
    )

    # Handle place ID finding
    place_id_found_count = 0
    place_id_warning_count = 0
    place_id_error_count = 0
    if find_place_id:
        place_id_found_count, place_id_warning_count, place_id_error_count = _handle_place_id_finding(
            user_id, username, all_users, restaurant_id, closest, dry_run
        )

    # Handle restaurant validation
    _handle_restaurant_validation(
        restaurants_to_validate,
        restaurant_counts,
        fix_mismatches,
        dry_run,
        service_level_updated_count,
        service_level_total_count,
        place_id_found_count,
        place_id_warning_count,
        place_id_error_count,
    )
