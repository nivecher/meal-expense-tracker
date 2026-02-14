"""CLI commands for restaurant management."""

from __future__ import annotations

import math
from typing import Optional

import click
from flask import Flask, current_app
from flask.cli import with_appcontext

from app.auth.models import User
from app.extensions import db
from app.restaurants.models import Restaurant
from app.utils.address_utils import (
    compare_addresses_semantic,
    normalize_country_to_iso2,
    normalize_state_to_usps,
)
from app.utils.phone_utils import normalize_phone_for_comparison
from app.utils.url_utils import normalize_website_for_comparison


@click.group("restaurant", context_settings={"help_option_names": ["-h", "--help"]})
def restaurant_cli() -> None:
    """Restaurant management commands."""


def register_commands(app: Flask) -> None:
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
    # name is required (not nullable), but check for empty string
    if not name:
        return None, []

    address = restaurant.full_address or ""

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
        if place_name and place_name.lower() == name.lower():
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

    if not restaurant_city:
        # If no city info, return first match (matches is non-empty due to check above)
        return matches[0]
    if not restaurant_state:
        # If no state info, return first match (matches is non-empty due to check above)
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
        if restaurant.user:
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

    if not restaurant.name:
        return None

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
        from typing import cast

        return cast(list[User], users)
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

            # Use CLI validation field mask (includes all tiers for full validation)
            from app.services.google_places_service import FIELD_MASKS

            place_data = places_service.get_place_details(
                restaurant.google_place_id, field_mask=FIELD_MASKS["cli_validation"]
            )

            if not place_data:
                return {
                    "valid": False,
                    "errors": ["Failed to retrieve place data from Google Places API"],
                }

            # Extract restaurant data using the service
            google_data = places_service.extract_restaurant_data(place_data)

            # PRO TIER: Extract website and price_level for validation
            # ENTERPRISE TIER: Extract rating
            google_website = google_data.get("website")
            google_price_level = google_data.get("price_level")

            return {
                "valid": True,
                "google_name": google_data.get("name"),  # PRO TIER: displayName
                "google_address": google_data.get("formatted_address"),  # ESSENTIALS TIER
                "google_rating": google_data.get("rating"),  # ENTERPRISE TIER
                "google_status": google_data.get("business_status", "OPERATIONAL"),  # PRO TIER
                "types": google_data.get("types", []),  # PRO TIER
                "primary_type": google_data.get("primary_type"),  # PRO TIER
                "google_phone": google_data.get("phone_number"),  # ENTERPRISE TIER: nationalPhoneNumber
                "google_website": google_website,  # PRO TIER: websiteUri
                "google_price_level": google_price_level,  # PRO TIER: priceLevel (may be deprecated)
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
    from typing import cast

    return cast(list[Restaurant], query.order_by(Restaurant.name).all())


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
    address_parts: list[str] = []
    if restaurant.address_line_1:
        address_parts.append(restaurant.address_line_1)
    if restaurant.address_line_2:
        address_parts.append(restaurant.address_line_2)
    if address_parts:
        click.echo(f"      Address: {', '.join(address_parts)}")

    # Display location information
    if restaurant.city:
        location_parts: list[str] = [restaurant.city]
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


def _check_restaurant_mismatches(
    restaurant: Restaurant,
    validation_result: dict,
    sections: frozenset[str] | None = None,
) -> tuple[list[str], dict[str, str]]:
    """Check for mismatches between restaurant data and Google data.

    Args:
        restaurant: Restaurant instance to check
        validation_result: Google Places validation result
        sections: If set, only run checks for these sections. If None, run all.
    """
    mismatches: list[str] = []
    fixes_to_apply: dict[str, str] = {}
    run_all = sections is None or len(sections) == 0

    def _should_check(section: str) -> bool:
        return run_all or section in (sections or frozenset())

    if _should_check("name"):
        _check_name_mismatch(restaurant, validation_result, mismatches, fixes_to_apply)

    if _should_check("address"):
        _check_address_mismatches(restaurant, validation_result, mismatches, fixes_to_apply)

    if _should_check("service_level"):
        _check_service_level_mismatch(restaurant, validation_result, mismatches, fixes_to_apply)

    if _should_check("price_level"):
        _check_price_level_mismatch(restaurant, validation_result, mismatches, fixes_to_apply)

    if _should_check("website"):
        _check_website_mismatch(restaurant, validation_result, mismatches, fixes_to_apply)

    if _should_check("cuisine"):
        _check_cuisine_mismatch(restaurant, validation_result, mismatches, fixes_to_apply)

    if _should_check("phone"):
        _check_phone_mismatch(restaurant, validation_result, mismatches, fixes_to_apply)

    if _should_check("type"):
        _check_type_mismatch(restaurant, validation_result, mismatches, fixes_to_apply)

    return mismatches, fixes_to_apply


def _check_name_mismatch(
    restaurant: Restaurant, validation_result: dict, mismatches: list, fixes_to_apply: dict
) -> None:
    """Check for name mismatches."""
    google_name = validation_result.get("google_name")
    restaurant_name = restaurant.name
    # restaurant_name is required (not nullable), so we only need to check google_name
    if not google_name or not isinstance(google_name, str):
        return

    # Type narrowing: google_name is now known to be str
    if google_name.lower() != restaurant_name.lower():
        mismatches.append(f"Name: '{restaurant_name}' vs Google: '{google_name}'")
        fixes_to_apply["name"] = google_name


def _check_address_mismatches(
    restaurant: Restaurant, validation_result: dict, mismatches: list, fixes_to_apply: dict
) -> None:
    """Check for address component mismatches (semantic for address lines, normalized for country)."""
    # Address lines: semantic comparison so "South State Highway" vs "S State Hwy" do not mismatch
    for google_field, restaurant_field, display_name in [
        ("google_address_line_1", "address_line_1", "Address Line 1"),
        ("google_address_line_2", "address_line_2", "Address Line 2"),
    ]:
        google_value = validation_result.get(google_field)
        restaurant_value = getattr(restaurant, restaurant_field)
        if not google_value and not restaurant_value:
            continue
        if not google_value:
            continue
        is_match, _ = compare_addresses_semantic(restaurant_value or "", google_value or "")
        if is_match:
            continue
        if restaurant_value:
            mismatches.append(f"{display_name}: '{restaurant_value}' vs Google: '{google_value}'")
            fixes_to_apply[restaurant_field] = google_value
        else:
            mismatches.append(f"{display_name}: '{restaurant_value or 'N/A'}' vs Google: '{google_value}'")
            fixes_to_apply[restaurant_field] = google_value

    # City and postal code: suggest Google value when stored is empty
    for google_field, restaurant_field, display_name in [
        ("google_city", "city", "City"),
        ("google_postal_code", "postal_code", "Postal Code"),
    ]:
        google_value = validation_result.get(google_field)
        restaurant_value = getattr(restaurant, restaurant_field)
        if not google_value:
            continue
        if not restaurant_value:
            mismatches.append(f"{display_name}: 'N/A' vs Google: '{google_value}'")
            fixes_to_apply[restaurant_field] = google_value
        elif google_value.lower() != restaurant_value.lower():
            mismatches.append(f"{display_name}: '{restaurant_value}' vs Google: '{google_value}'")
            fixes_to_apply[restaurant_field] = google_value

    # Country: normalize to ISO 2-letter (USA/United States -> US) for comparison and fix
    google_country = validation_result.get("google_country")
    restaurant_country = restaurant.country
    norm_google = normalize_country_to_iso2(google_country or "")
    norm_restaurant = normalize_country_to_iso2(restaurant_country or "")
    if norm_google and norm_restaurant and norm_google != norm_restaurant:
        mismatches.append(f"Country: '{restaurant_country}' vs Google: '{google_country}'")
        fixes_to_apply["country"] = norm_google
    elif norm_google and not norm_restaurant:
        mismatches.append(f"Country: 'N/A' vs Google: '{google_country}'")
        fixes_to_apply["country"] = norm_google

    # State: specialized matching (us.states) and suggest 2-letter fix
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

    # Google has no state - nothing to check
    if not (google_state or google_state_long or google_state_short):
        return

    # Stored is empty but Google has state - suggest fix (same as city/postal_code)
    if not current_state or not str(current_state).strip():
        display_state = google_state_long or google_state or google_state_short
        mismatches.append(f"State: 'N/A' vs Google: '{display_state}'")
        two_letter = validation_result.get("google_state_short") or normalize_state_to_usps(
            validation_result.get("google_state") or validation_result.get("google_state_long") or ""
        )
        fixes_to_apply["state"] = two_letter or google_state_long or google_state or google_state_short
        return

    # Check direct string matches first
    if google_state:
        if _states_match_directly(current_state, google_state or "", google_state_long or "", google_state_short or ""):
            return

    # Try US library matching as fallback
    if current_state and google_state:
        if _states_match_with_us_library(
            current_state, google_state or "", google_state_long or "", google_state_short or ""
        ):
            return

    # No matches found - report mismatch; suggest USPS 2-letter state for fix
    display_state = google_state_long or google_state
    mismatches.append(f"State: '{current_state}' vs Google: '{display_state}'")
    two_letter = validation_result.get("google_state_short") or normalize_state_to_usps(
        validation_result.get("google_state") or validation_result.get("google_state_long") or ""
    )
    fixes_to_apply["state"] = two_letter or google_state_long or google_state


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
    import us  # type: ignore[import-untyped]

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
        # Handle both tuple (level, confidence) and dict formats
        if isinstance(google_service_level_data, tuple):
            google_service_level = google_service_level_data[0]
            confidence_value = google_service_level_data[1] if len(google_service_level_data) > 1 else None
        elif isinstance(google_service_level_data, dict):
            google_service_level = google_service_level_data.get("level")
            confidence_value = google_service_level_data.get("confidence")
        else:
            return  # Invalid format, skip

        # Convert confidence to float if it's not already
        if confidence_value is not None:
            try:
                confidence = float(confidence_value)
            except (ValueError, TypeError):
                confidence = 0.0
        else:
            confidence = 0.0

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
    google_price_level = validation_result.get("google_price_level")

    if google_price_level is not None:
        from app.services.google_places_service import get_google_places_service

        places_service = get_google_places_service()
        google_price_level_int = places_service.convert_price_level_to_int(google_price_level)

        restaurant_price_level = restaurant.price_level

        # Check for mismatch (including None vs non-None)
        if restaurant_price_level != google_price_level_int:
            restaurant_display = _format_price_level_display(restaurant_price_level)
            google_display = _format_price_level_display(google_price_level_int)
            mismatches.append(f"Price Level: '{restaurant_display}' vs Google: '{google_display}'")
            fixes_to_apply["price_level"] = google_price_level_int


def _check_website_mismatch(
    restaurant: Restaurant, validation_result: dict, mismatches: list, fixes_to_apply: dict
) -> None:
    """Check for website mismatches (normalized: strip params, trailing slash)."""
    google_website = validation_result.get("google_website")

    if google_website is not None:
        restaurant_website = restaurant.website
        norm_restaurant = normalize_website_for_comparison(restaurant_website)
        norm_google = normalize_website_for_comparison(google_website)

        if norm_google and norm_restaurant != norm_google:
            restaurant_display = restaurant_website or "Not set"
            google_display = google_website or "Not set"
            mismatches.append(f"Website: '{restaurant_display}' vs Google: '{google_display}'")
            fixes_to_apply["website"] = google_website


def _check_cuisine_mismatch(
    restaurant: Restaurant, validation_result: dict, mismatches: list, fixes_to_apply: dict
) -> None:
    """Check for cuisine mismatches (case-insensitive)."""
    google_cuisine = validation_result.get("google_cuisine")

    if google_cuisine is not None:
        restaurant_cuisine = restaurant.cuisine

        if not restaurant_cuisine or restaurant_cuisine.strip().lower() != google_cuisine.strip().lower():
            restaurant_display = restaurant_cuisine or "Not set"
            google_display = google_cuisine or "Not set"
            mismatches.append(f"Cuisine: '{restaurant_display}' vs Google: '{google_display}'")
            fixes_to_apply["cuisine"] = google_cuisine


def _check_phone_mismatch(
    restaurant: Restaurant, validation_result: dict, mismatches: list, fixes_to_apply: dict
) -> None:
    """Check for phone mismatches (normalized: digits-only comparison)."""
    google_phone = validation_result.get("google_phone")

    if google_phone is not None:
        restaurant_phone = restaurant.phone
        norm_restaurant = normalize_phone_for_comparison(restaurant_phone)
        norm_google = normalize_phone_for_comparison(google_phone)

        if norm_google and norm_restaurant != norm_google:
            restaurant_display = restaurant_phone or "Not set"
            google_display = google_phone or "Not set"
            mismatches.append(f"Phone: '{restaurant_display}' vs Google: '{google_display}'")
            fixes_to_apply["phone"] = google_phone


# Website validation restored - PRO TIER: websiteUri


def _check_type_mismatch(
    restaurant: Restaurant, validation_result: dict, mismatches: list, fixes_to_apply: dict
) -> None:
    """Check for type mismatches (direct comparison with Google primary_type)."""
    google_primary_type = validation_result.get("primary_type")

    if google_primary_type is not None:
        restaurant_type = restaurant.type

        if restaurant_type != google_primary_type:
            restaurant_display = restaurant_type or "Not set"
            google_display = google_primary_type or "Not set"
            mismatches.append(f"Type: '{restaurant_display}' vs Google: '{google_display}'")
            fixes_to_apply["type"] = google_primary_type


def _prompt_yn_no_default(message: str) -> bool:
    """Prompt for y/n with no default - user must explicitly respond y or n."""

    def _parse_yn(value: str) -> bool:
        v = (value or "").strip().lower()
        if v in ("y", "yes"):
            return True
        if v in ("n", "no"):
            return False
        raise click.BadParameter("Please enter y or n")

    return click.prompt(message, type=_parse_yn)


def _get_fix_display_name(fix_key: str) -> str:
    """Return human-readable name for a fix key."""
    display_names = {
        "name": "Name",
        "address_line_1": "Address line 1",
        "address_line_2": "Address line 2",
        "city": "City",
        "state": "State",
        "postal_code": "Postal code",
        "country": "Country",
        "service_level": "Service level",
        "price_level": "Price level",
        "website": "Website",
        "cuisine": "Cuisine",
        "phone": "Phone",
        "type": "Type",
    }
    return display_names.get(fix_key, fix_key.replace("_", " ").title())


def _apply_restaurant_fixes(
    restaurant: Restaurant,
    fixes_to_apply: dict[str, str],
    dry_run: bool,
    interactive: bool = False,
) -> bool:
    """Apply fixes to restaurant data and return success status."""
    if dry_run:
        click.echo(f"   🔧 Would fix: {', '.join(fixes_to_apply.keys())}")
        return True

    to_apply = fixes_to_apply
    if interactive:
        to_apply = {}
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
            "website": "website",
            "cuisine": "cuisine",
            "phone": "phone",
            "type": "type",
        }
        for fix_key, new_value in fixes_to_apply.items():
            field_name = field_mappings.get(fix_key, fix_key)
            old_value = getattr(restaurant, field_name, None)
            old_display = str(old_value) if old_value is not None and str(old_value) else "(not set)"
            new_display = str(new_value) if new_value is not None and str(new_value) else "(not set)"
            display_name = _get_fix_display_name(fix_key)
            if _prompt_yn_no_default(f"   Apply {display_name}: {old_display} → {new_display}? [y/n]"):
                to_apply[fix_key] = new_value
        if not to_apply:
            click.echo("   ⏭️  Skipped all fixes")
            return False

    try:
        _apply_restaurant_field_fixes(restaurant, to_apply)
        db.session.commit()
        click.echo(f"   ✅ Fixed: {', '.join(to_apply.keys())}")
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
        "price_level": "price_level",  # PRO TIER: priceLevel (may be deprecated)
        "website": "website",  # PRO TIER: websiteUri
        "cuisine": "cuisine",
        "phone": "phone",
        "type": "type",
    }

    for fix_key, field_name in field_mappings.items():
        if fix_key in fixes_to_apply:
            setattr(restaurant, field_name, fixes_to_apply[fix_key])


def _format_address_value(value: str | None) -> str:
    """Format address value for display, using '(not set)' for empty."""
    return value if value else "(not set)"


def _address_fields_differ(restaurant: Restaurant, validation_result: dict) -> bool:
    """Return True if any address field differs between stored and Google data."""
    # Address lines: semantic comparison
    for google_field, restaurant_field in [
        ("google_address_line_1", "address_line_1"),
        ("google_address_line_2", "address_line_2"),
    ]:
        google_val = validation_result.get(google_field)
        stored_val = getattr(restaurant, restaurant_field)
        if not google_val and not stored_val:
            continue
        if google_val:
            is_match, _ = compare_addresses_semantic(stored_val or "", google_val or "")
            if not is_match:
                return True
    # City, postal code: simple comparison
    for google_field, restaurant_field in [
        ("google_city", "city"),
        ("google_postal_code", "postal_code"),
    ]:
        google_val = validation_result.get(google_field)
        stored_val = getattr(restaurant, restaurant_field)
        if google_val and (not stored_val or stored_val.lower() != google_val.lower()):
            return True
    # Country: normalized comparison
    norm_google = normalize_country_to_iso2(validation_result.get("google_country") or "")
    norm_stored = normalize_country_to_iso2(restaurant.country or "")
    if norm_google and norm_stored != norm_google:
        return True
    if norm_google and not restaurant.country:
        return True
    # State: show if stored differs from any Google state format
    stored_state = (restaurant.state or "").strip().lower()
    google_states = [
        validation_result.get("google_state_short"),
        validation_result.get("google_state"),
        validation_result.get("google_state_long"),
    ]
    google_vals = [g.strip().lower() for g in google_states if g and g.strip()]
    if google_vals and not stored_state:
        return True
    if stored_state and google_vals:
        if stored_state not in google_vals:
            return True
    return False


def _address_field_differs(
    restaurant: Restaurant,
    validation_result: dict,
    restaurant_field: str,
    google_field: str,
) -> bool:
    """Return True if the given address field differs between stored and Google data."""
    stored = getattr(restaurant, restaurant_field)
    google_val = validation_result.get(google_field)

    if restaurant_field in ("address_line_1", "address_line_2"):
        if not google_val and not stored:
            return False
        if not google_val:
            return False
        is_match, _ = compare_addresses_semantic(stored or "", google_val or "")
        return not is_match
    if restaurant_field in ("city", "postal_code"):
        if not google_val and not stored:
            return False
        return bool(google_val and (not stored or stored.lower() != google_val.lower()))
    if restaurant_field == "country":
        norm_google = normalize_country_to_iso2(google_val or "")
        norm_stored = normalize_country_to_iso2(restaurant.country or "")
        if not norm_google:
            return False
        return norm_stored != norm_google or not restaurant.country
    if restaurant_field == "state":
        stored_state = (restaurant.state or "").strip().lower()
        google_states = [
            validation_result.get("google_state_short"),
            validation_result.get("google_state"),
            validation_result.get("google_state_long"),
        ]
        google_vals = [g.strip().lower() for g in google_states if g and g.strip()]
        if not google_vals:
            return False
        if not stored_state:
            return True
        return stored_state not in google_vals
    return False


def _display_address_comparison(restaurant: Restaurant, validation_result: dict, quiet: bool = False) -> None:
    """Display field-by-field address comparison between stored and Google data."""
    if not _address_fields_differ(restaurant, validation_result):
        return

    click.echo("   📍 Address Comparison (by field):")

    address_field_specs = [
        ("address_line_1", "Address Line 1", "google_address_line_1"),
        ("address_line_2", "Address Line 2", "google_address_line_2"),
        ("city", "City", "google_city"),
        ("state", "State", "google_state"),
        ("postal_code", "Postal Code", "google_postal_code"),
        ("country", "Country", "google_country"),
    ]

    for restaurant_field, display_name, google_field in address_field_specs:
        if quiet and not _address_field_differs(restaurant, validation_result, restaurant_field, google_field):
            continue
        stored = getattr(restaurant, restaurant_field)
        google_val = validation_result.get(google_field)
        if restaurant_field == "state" and validation_result.get("google_state_short"):
            google_val = validation_result.get("google_state_short")
        elif restaurant_field == "state" and not google_val:
            google_val = validation_result.get("google_state_long") or validation_result.get("google_state")
        stored_fmt = _format_address_value(stored)
        google_fmt = _format_address_value(google_val)
        click.echo(f"      {display_name}:  Stored: {stored_fmt!r}  |  Google: {google_fmt!r}")


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
    if validation_result.get("google_price_level") is not None:
        price_level = validation_result.get("google_price_level")
        price_level_display = _format_price_level_display(price_level)
        click.echo(f"   💲 Price Level: {price_level_display}")
    # Primary type first (clear and prominent), then full types list in Google order
    primary_type = validation_result.get("primary_type")
    if primary_type:
        click.echo(f"   🏷️  Primary type: {primary_type}")
    if validation_result.get("types"):
        types_data = validation_result["types"]
        if isinstance(types_data, list):
            types_str = ", ".join(types_data[:5])  # Show first 5 (primary is first)
        else:
            types_str = str(types_data)
        click.echo(f"   🏷️  Types: {types_str}")


def _display_google_service_info(validation_result: dict) -> None:
    """Display Google service level information."""
    google_service_level_data = validation_result.get("google_service_level")
    if google_service_level_data:
        # Handle both tuple (level, confidence) and dict formats
        if isinstance(google_service_level_data, tuple):
            service_level = google_service_level_data[0]
            confidence_value = google_service_level_data[1] if len(google_service_level_data) > 1 else None
        elif isinstance(google_service_level_data, dict):
            service_level = google_service_level_data.get("level")
            confidence_value = google_service_level_data.get("confidence")
        else:
            return  # Invalid format, skip

        # Convert confidence to float if it's not already
        if confidence_value is not None:
            try:
                confidence = float(confidence_value)
            except (ValueError, TypeError):
                confidence = 0.0
        else:
            confidence = 0.0

        if service_level != "unknown":
            from app.restaurants.services import get_service_level_display_info

            display_info = get_service_level_display_info(service_level)
            click.echo(f"   🍽️  Service Level: {display_info['display_name']} (confidence: {confidence:.2f})")


def _format_price_level_display(price_level: int | None) -> str:
    """Format price level for display.

    Args:
        price_level: Price level integer (0-4) or None

    Returns:
        Formatted price level string
    """
    if price_level is None:
        return "Not set"

    price_level_mapping = {
        0: "Free",
        1: "$ (Inexpensive)",
        2: "$$ (Moderate)",
        3: "$$$ (Expensive)",
        4: "$$$$ (Very Expensive)",
    }

    return price_level_mapping.get(price_level, str(price_level))


def _echo_restaurant_header(restaurant: Restaurant, quiet: bool = False) -> None:
    """Output restaurant context (name, ID, user). Compact in quiet mode."""
    user_part = f" [{restaurant.user.username}]" if restaurant.user and not quiet else ""
    if quiet:
        click.echo(f"\n🍽️  {restaurant.name} (ID: {restaurant.id}){user_part}")
    else:
        click.echo(f"\n🍽️  {restaurant.name} (ID: {restaurant.id})")
        if restaurant.user:
            click.echo(f"   User: {restaurant.user.username}")
        click.echo(f"   Google Place ID: {restaurant.google_place_id}")
        click.echo(f"   Full Address: {restaurant.full_address}")


def _process_restaurant_validation(
    restaurant: Restaurant,
    fix_mismatches: bool,
    dry_run: bool,
    validation_sections: frozenset[str] | None = None,
    quiet: bool = False,
    show_mismatches_only: bool = False,
    interactive: bool = False,
) -> tuple[str, bool]:
    """Process validation for a single restaurant and return status and fix success."""
    validation_result = _validate_restaurant_with_google(restaurant)

    if validation_result["valid"] is True:
        # Check for mismatches (optionally limited to specific sections)
        mismatches, fixes_to_apply = _check_restaurant_mismatches(
            restaurant, validation_result, sections=validation_sections
        )

        if mismatches:
            # Show details first so user can see Google data before interactive prompts
            _echo_restaurant_header(restaurant, quiet=quiet)
            if not quiet:
                _display_google_info(validation_result)

            click.echo("   ⚠️  Has mismatches:")
            for mismatch in mismatches:
                click.echo(f"      - {mismatch}")

            # Show address comparison only when validating address section
            if validation_sections is None or "address" in (validation_sections or frozenset()):
                _display_address_comparison(restaurant, validation_result, quiet=quiet)

            fixed = False
            if fix_mismatches and fixes_to_apply:
                fixed = _apply_restaurant_fixes(restaurant, fixes_to_apply, dry_run, interactive=interactive)
            return "valid", fixed
        else:
            # Valid with no mismatches - skip output when showing mismatches only
            if not show_mismatches_only:
                _echo_restaurant_header(restaurant, quiet=quiet)
                if not quiet:
                    _display_google_info(validation_result)
                click.echo("   ✅ Valid")
            return "valid", False

    elif validation_result["valid"] is False:
        # Invalid - always show in quiet mode (it's a problem)
        _echo_restaurant_header(restaurant, quiet=quiet)
        click.echo("   ❌ Invalid")
        for error in validation_result["errors"]:
            click.echo(f"      Error: {error}")
        return "invalid", False
    else:
        # Cannot validate - always show in quiet mode (it's a problem)
        _echo_restaurant_header(restaurant, quiet=quiet)
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
    validation_sections: frozenset[str] | None = None,
    quiet: bool = False,
    show_mismatches_only: bool = False,
    interactive: bool = False,
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

    if show_mismatches_only:
        click.echo("🔍 Showing only restaurants with mismatches or errors\n")
    if quiet:
        click.echo("🔇 Quiet mode: reduced output detail\n")

    valid_count = 0
    invalid_count = 0
    error_count = 0
    fixed_count = 0
    mismatch_count = 0

    for restaurant in restaurants_to_validate:
        status, fixed = _process_restaurant_validation(
            restaurant,
            fix_mismatches,
            dry_run,
            validation_sections=validation_sections,
            quiet=quiet,
            show_mismatches_only=show_mismatches_only,
            interactive=interactive,
        )

        if status == "valid":
            valid_count += 1

            # Check for mismatches (same sections filter for count)
            validation_result = _validate_restaurant_with_google(restaurant)
            if validation_result["valid"] is True:
                mismatches, _ = _check_restaurant_mismatches(
                    restaurant, validation_result, sections=validation_sections
                )
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
    if restaurant.user:
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


def _build_validation_sections(
    address: bool,
    type_section: bool,
    name_section: bool,
    service_level: bool,
    price_level: bool,
    website: bool,
    cuisine: bool,
    phone: bool,
) -> frozenset[str] | None:
    """Build validation sections set from CLI flags. None means validate all."""
    sections = []
    if address:
        sections.append("address")
    if type_section:
        sections.append("type")
    if name_section:
        sections.append("name")
    if service_level:
        sections.append("service_level")
    if price_level:
        sections.append("price_level")
    if website:
        sections.append("website")
    if cuisine:
        sections.append("cuisine")
    if phone:
        sections.append("phone")
    return frozenset(sections) if sections else None


@click.command("validate")
@click.option("--user-id", type=int, help="Specific user ID to validate restaurants for")
@click.option("--username", type=str, help="Specific username to validate restaurants for")
@click.option("--all-users", is_flag=True, help="Validate restaurants for all users")
@click.option("--restaurant-id", type=int, help="Validate a specific restaurant by ID")
@click.option("--fix-mismatches", is_flag=True, help="Fix mismatches from Google data")
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Prompt to confirm or deny each fix (use with --fix-mismatches)",
)
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
@click.option(
    "--mismatches",
    "-m",
    is_flag=True,
    help="Only show restaurants with mismatches or errors (hide valid restaurants)",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Reduce output detail (compact headers, omit Google info)",
)
@click.option("--address", is_flag=True, help="Only validate address fields")
@click.option("--type", "type_section", is_flag=True, help="Only validate restaurant type")
@click.option("--name", "name_section", is_flag=True, help="Only validate restaurant name")
@click.option("--service-level", is_flag=True, help="Only validate service level")
@click.option("--price-level", is_flag=True, help="Only validate price level")
@click.option("--website", is_flag=True, help="Only validate website")
@click.option("--cuisine", is_flag=True, help="Only validate cuisine")
@click.option("--phone", is_flag=True, help="Only validate phone")
@with_appcontext
def validate_restaurants(
    user_id: int | None,
    username: str | None,
    all_users: bool,
    restaurant_id: int | None,
    fix_mismatches: bool,
    interactive: bool,
    update_service_levels: bool,
    find_place_id: bool,
    closest: bool,
    dry_run: bool,
    mismatches: bool,
    quiet: bool,
    address: bool,
    type_section: bool,
    name_section: bool,
    service_level: bool,
    price_level: bool,
    website: bool,
    cuisine: bool,
    phone: bool,
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
        flask restaurant validate --address --user-id 1
        flask restaurant validate --type --restaurant-id 123
        flask restaurant validate --address --type --cuisine --user-id 1
        flask restaurant validate --mismatches --all-users
        flask restaurant validate -m -q --all-users
        flask restaurant validate --fix-mismatches -i --user-id 1
    """
    validation_sections = _build_validation_sections(
        address, type_section, name_section, service_level, price_level, website, cuisine, phone
    )
    if validation_sections:
        click.echo(f"🔍 Validating sections: {', '.join(sorted(validation_sections))}")

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
        validation_sections=validation_sections,
        quiet=quiet,
        show_mismatches_only=mismatches,
        interactive=interactive,
        service_level_updated_count=service_level_updated_count,
        service_level_total_count=service_level_total_count,
        place_id_found_count=place_id_found_count,
        place_id_warning_count=place_id_warning_count,
        place_id_error_count=place_id_error_count,
    )
