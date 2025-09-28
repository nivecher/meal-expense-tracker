"""Template filters for the application."""

from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote_plus

from flask import Flask


def time_ago(dt: datetime) -> str:
    """Return a string representing time since the given datetime.

    Args:
        dt: The datetime to calculate time since

    Returns:
        str: A string like "3 days ago" or "5 hours ago"
    """
    if not dt:
        return "Never"

    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    diff = now - dt
    periods = (
        (diff.days // 365, "year", "years"),
        (diff.days // 30, "month", "months"),
        (diff.days // 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds // 3600, "hour", "hours"),
        (diff.seconds // 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:
        if period > 0:
            return f"{period} {singular if period == 1 else plural} ago"
    return "just now"


def _extract_restaurant_data(restaurant_data) -> Optional[dict]:
    """Extract restaurant data from object or dictionary."""
    if isinstance(restaurant_data, dict):
        return {
            "name": restaurant_data.get("name", ""),
            "google_place_id": restaurant_data.get("google_place_id"),
            "address": restaurant_data.get("address", ""),
            "city": restaurant_data.get("city", ""),
            "state": restaurant_data.get("state", ""),
            "postal_code": restaurant_data.get("postal_code", ""),
        }

    # Try to access as object attributes
    try:
        return {
            "name": getattr(restaurant_data, "name", ""),
            "google_place_id": getattr(restaurant_data, "google_place_id", None),
            "address": getattr(restaurant_data, "address", ""),
            "city": getattr(restaurant_data, "city", ""),
            "state": getattr(restaurant_data, "state", ""),
            "postal_code": getattr(restaurant_data, "postal_code", ""),
        }
    except (AttributeError, TypeError):
        return None


def _build_search_query(data: dict) -> Optional[str]:
    """Build search query from restaurant data."""
    search_parts = []

    # Always include restaurant name
    if data["name"]:
        search_parts.append(data["name"])

    # Add address details in order of specificity
    if data["address"]:
        search_parts.append(data["address"])
    elif data["city"]:
        search_parts.append(data["city"])

    # Add city if not already included in address
    if data["city"] and data["address"] and data["city"].lower() not in data["address"].lower():
        search_parts.append(data["city"])

    # Add state and postal code
    if data["state"]:
        search_parts.append(data["state"])
    if data["postal_code"]:
        search_parts.append(data["postal_code"])

    if search_parts:
        search_query = ", ".join(search_parts)
        return quote_plus(search_query)

    return None


def google_maps_url(restaurant_data) -> Optional[str]:
    """Generate a Google Maps URL for a restaurant object or dictionary (API token-free).

    Args:
        restaurant_data: Restaurant object or dictionary containing restaurant information

    Returns:
        Optional[str]: Google Maps URL or None if no location data is available
    """
    if not restaurant_data:
        return None

    # Handle Restaurant objects with the method
    if hasattr(restaurant_data, "get_google_maps_url"):
        return restaurant_data.get_google_maps_url()

    # Extract data from dictionary or object
    data = _extract_restaurant_data(restaurant_data)
    if not data:
        return None

    # First preference: Use place_id format with restaurant name
    if data["google_place_id"] and data["name"]:
        restaurant_name = quote_plus(data["name"])
        return f"https://www.google.com/maps/search/?api=1&query={restaurant_name}&query_place_id={data['google_place_id']}"

    # Second preference: Use search-based URL
    encoded_query = _build_search_query(data)
    if encoded_query:
        return f"https://www.google.com/maps/search/?api=1&query={encoded_query}"

    return None


def get_state_abbreviation(state: Optional[str]) -> Optional[str]:
    """Convert state name to abbreviation.

    Args:
        state: State name (full name or abbreviation)

    Returns:
        State abbreviation or original value if conversion fails
    """
    if not state or not state.strip():
        return state

    state_clean = state.strip()

    # US state abbreviations mapping
    state_abbreviations = {
        "Alabama": "AL",
        "Alaska": "AK",
        "Arizona": "AZ",
        "Arkansas": "AR",
        "California": "CA",
        "Colorado": "CO",
        "Connecticut": "CT",
        "Delaware": "DE",
        "Florida": "FL",
        "Georgia": "GA",
        "Hawaii": "HI",
        "Idaho": "ID",
        "Illinois": "IL",
        "Indiana": "IN",
        "Iowa": "IA",
        "Kansas": "KS",
        "Kentucky": "KY",
        "Louisiana": "LA",
        "Maine": "ME",
        "Maryland": "MD",
        "Massachusetts": "MA",
        "Michigan": "MI",
        "Minnesota": "MN",
        "Mississippi": "MS",
        "Missouri": "MO",
        "Montana": "MT",
        "Nebraska": "NE",
        "Nevada": "NV",
        "New Hampshire": "NH",
        "New Jersey": "NJ",
        "New Mexico": "NM",
        "New York": "NY",
        "North Carolina": "NC",
        "North Dakota": "ND",
        "Ohio": "OH",
        "Oklahoma": "OK",
        "Oregon": "OR",
        "Pennsylvania": "PA",
        "Rhode Island": "RI",
        "South Carolina": "SC",
        "South Dakota": "SD",
        "Tennessee": "TN",
        "Texas": "TX",
        "Utah": "UT",
        "Vermont": "VT",
        "Virginia": "VA",
        "Washington": "WA",
        "West Virginia": "WV",
        "Wisconsin": "WI",
        "Wyoming": "WY",
    }

    # Check if it's already an abbreviation (2 characters)
    if len(state_clean) == 2 and state_clean.upper() in state_abbreviations.values():
        return state_clean.upper()

    # Try to find the abbreviation for the full state name
    abbreviation = state_abbreviations.get(state_clean.title())
    if abbreviation:
        return abbreviation

    # If not found, try with us library as fallback
    try:
        import us

        state_obj = us.states.lookup(state_clean)
        if state_obj:
            return state_obj.abbr
    except ImportError:
        # us library not available, continue with fallback
        pass
    except Exception:  # nosec B110
        # Error in us library lookup, continue with fallback
        pass

    # Return original value if no conversion found
    return state_clean


def format_location_display(
    address: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    include_postal_code: bool = False,
    postal_code: Optional[str] = None,
) -> str:
    """Format location for display in restaurant tables.

    Args:
        address: Street address
        city: City name
        state: State name (will be converted to abbreviation)
        include_postal_code: Whether to include postal code
        postal_code: Postal code

    Returns:
        Formatted location string
    """
    parts = []

    # Add address if provided
    if address:
        parts.append(address)

    # Add city and state abbreviation
    if city and state:
        state_abbr = get_state_abbreviation(state)
        parts.append(f"{city}, {state_abbr}")
    elif city:
        parts.append(city)
    elif state:
        state_abbr = get_state_abbreviation(state)
        parts.append(state_abbr)

    # Add postal code if requested
    if include_postal_code and postal_code:
        if parts:
            parts.append(postal_code)
        else:
            parts.append(postal_code)

    return ", ".join(parts) if parts else "No location"


def format_location_with_within(
    address: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    located_within: Optional[str] = None,
    include_postal_code: bool = False,
    postal_code: Optional[str] = None,
) -> tuple[str, Optional[str]]:
    """Format location with separate lines for location within.

    Args:
        address: Street address
        city: City name
        state: State name (will be converted to abbreviation)
        located_within: Location within (e.g., mall, airport, hotel)
        include_postal_code: Whether to include postal code
        postal_code: Postal code

    Returns:
        Tuple of (main_location, location_within)
    """
    main_location = format_location_display(
        address=address, city=city, state=state, include_postal_code=include_postal_code, postal_code=postal_code
    )

    # Clean up located_within - it should not be the same as city
    location_within = None
    if located_within and located_within.strip():
        cleaned_within = located_within.strip()
        # Don't show "located within" if it's the same as the city
        if cleaned_within.lower() != city.lower() if city else True:
            location_within = cleaned_within

    return main_location, location_within


def restaurant_location_display(restaurant) -> tuple[str, Optional[str]]:
    """Format restaurant location for display with location within.

    Args:
        restaurant: Restaurant object with city, state, located_within attributes

    Returns:
        Tuple of (main_location, location_within)
    """

    # Extract data from restaurant object and clean up "None" strings
    def clean_value(value):
        if value is None or value == "None" or value == "":
            return None
        return value.strip() if isinstance(value, str) else value

    city = clean_value(getattr(restaurant, "city", None))
    state = clean_value(getattr(restaurant, "state", None))
    located_within = clean_value(getattr(restaurant, "located_within", None))
    postal_code = clean_value(getattr(restaurant, "postal_code", None))
    address = getattr(restaurant, "address", None)

    # If no city/state/postal_code and no address, return "No location"
    if not (city or state or postal_code) and not address:
        return "No location", None

    return format_location_with_within(
        address=address,
        city=city,
        state=state,
        located_within=located_within,
        include_postal_code=False,
        postal_code=postal_code,
    )


def restaurant_table_location_display(restaurant) -> tuple[str, Optional[str]]:
    """Template filter to display restaurant location for table view (city, state only).

    Args:
        restaurant: Restaurant object

    Returns:
        Tuple of (city_state, location_within)
    """

    # Extract data from restaurant object and clean up "None" strings
    def clean_value(value):
        if value is None or value == "None" or value == "":
            return None
        return value.strip() if isinstance(value, str) else value

    city = clean_value(getattr(restaurant, "city", None))
    state = clean_value(getattr(restaurant, "state", None))
    located_within = clean_value(getattr(restaurant, "located_within", None))

    # If no city/state, return "No location"
    if not (city or state):
        return "No location", None

    # Format city and state only (no address)
    city_state = format_location_display(
        address=None, city=city, state=state, include_postal_code=False, postal_code=None  # No address for table view
    )

    # Clean up located_within - it should not be the same as city
    location_within = None
    if located_within and located_within.strip():
        cleaned_within = located_within.strip()
        # Don't show "located within" if it's the same as the city
        if cleaned_within.lower() != city.lower() if city else True:
            location_within = cleaned_within

    return city_state, location_within


def _clean_value(value):
    """Clean up 'None' strings and empty values."""
    if value is None or value == "None" or value == "":
        return None
    return value.strip() if isinstance(value, str) else value


def _get_restaurant_value(restaurant, key, default=None):
    """Get value from restaurant object or dictionary."""
    if hasattr(restaurant, key):
        return getattr(restaurant, key, default)
    elif isinstance(restaurant, dict):
        return restaurant.get(key, default)
    return default


def _build_address_parts(name, located_within, address, city, state, postal_code):
    """Build address parts list."""
    address_parts = []

    if name:
        if located_within:
            address_parts.append(f"{name} - {located_within}")
        else:
            address_parts.append(name)

    if address:
        address_parts.append(address)

    if city and state:
        state_abbr = get_state_abbreviation(state)
        address_parts.append(f"{city}, {state_abbr}")
    elif city:
        address_parts.append(city)
    elif state:
        state_abbr = get_state_abbreviation(state)
        address_parts.append(state_abbr)

    if postal_code:
        address_parts.append(postal_code)

    return address_parts


def restaurant_address_display(restaurant) -> tuple[str, Optional[str]]:
    """Template filter to display restaurant address with name and location within.

    Args:
        restaurant: Restaurant object or dictionary

    Returns:
        Tuple of (address_with_name, location_within)
    """
    # Extract restaurant data
    name = _get_restaurant_value(restaurant, "name", "")
    located_within = _clean_value(_get_restaurant_value(restaurant, "located_within"))
    address = _get_restaurant_value(restaurant, "address")
    city = _clean_value(_get_restaurant_value(restaurant, "city"))
    state = _clean_value(_get_restaurant_value(restaurant, "state"))
    postal_code = _clean_value(_get_restaurant_value(restaurant, "postal_code"))

    # Build and format address
    address_parts = _build_address_parts(name, located_within, address, city, state, postal_code)
    address_with_name = ", ".join(address_parts) if address_parts else "No address"

    return address_with_name, located_within


def restaurant_address_only(restaurant) -> str:
    """Template filter to display restaurant address only (no name).

    Args:
        restaurant: Restaurant object

    Returns:
        Formatted address string with line breaks
    """

    # Extract data from restaurant object and clean up "None" strings
    def clean_value(value):
        if value is None or value == "None" or value == "":
            return None
        return value.strip() if isinstance(value, str) else value

    address_line_1 = _clean_value(_get_restaurant_value(restaurant, "address_line_1"))
    address_line_2 = _clean_value(_get_restaurant_value(restaurant, "address_line_2"))
    city = _clean_value(_get_restaurant_value(restaurant, "city"))
    state = _clean_value(_get_restaurant_value(restaurant, "state"))
    postal_code = _clean_value(_get_restaurant_value(restaurant, "postal_code"))

    # Create address parts
    address_lines = []

    # Add address line 1 if available
    if address_line_1:
        address_lines.append(address_line_1)

    # Add address line 2 if available
    if address_line_2:
        address_lines.append(address_line_2)

    # Add city, state, and postal code on second line
    city_state_parts = []
    if city and state:
        state_abbr = get_state_abbreviation(state)
        city_state_parts.append(f"{city}, {state_abbr}")
    elif city:
        city_state_parts.append(city)
    elif state:
        state_abbr = get_state_abbreviation(state)
        city_state_parts.append(state_abbr)

    # Add postal code if available
    if postal_code:
        city_state_parts.append(postal_code)

    if city_state_parts:
        address_lines.append(", ".join(city_state_parts))

    return "\n".join(address_lines) if address_lines else "No address"


def _create_city_state_line(city, state, postal_code):
    """Create city, state, postal code line."""
    city_state_parts = []
    if city and state:
        state_abbr = get_state_abbreviation(state)
        city_state_parts.append(f"{city}, {state_abbr}")
    elif city:
        city_state_parts.append(city)
    elif state:
        state_abbr = get_state_abbreviation(state)
        city_state_parts.append(state_abbr)

    if postal_code:
        city_state_parts.append(postal_code)

    return city_state_parts


def restaurant_address_with_maps(restaurant) -> str:
    """Template filter to display restaurant address (maps link handled in template).

    Args:
        restaurant: Restaurant object or dictionary

    Returns:
        Formatted address string
    """
    address_line_1 = _clean_value(_get_restaurant_value(restaurant, "address_line_1"))
    address_line_2 = _clean_value(_get_restaurant_value(restaurant, "address_line_2"))
    city = _clean_value(_get_restaurant_value(restaurant, "city"))
    state = _clean_value(_get_restaurant_value(restaurant, "state"))
    postal_code = _clean_value(_get_restaurant_value(restaurant, "postal_code"))

    # Create address parts
    address_lines = []

    if address_line_1:
        address_lines.append(address_line_1)

    if address_line_2:
        address_lines.append(address_line_2)

    # Create city/state line
    city_state_parts = _create_city_state_line(city, state, postal_code)
    if city_state_parts:
        city_state_line = ", ".join(city_state_parts)
        address_lines.append(city_state_line)

    return "\n".join(address_lines) if address_lines else "No address"


def split_string(text: str, delimiter: str = "\n") -> list:
    """Template filter to split a string by delimiter.

    Args:
        text: String to split
        delimiter: Delimiter to split on (default: newline)

    Returns:
        List of strings
    """
    if not text:
        return []
    return text.split(delimiter)


def init_app(app: Flask):
    """Register the filter with the Flask app.

    Args:
        app: The Flask application instance
    """
    app.jinja_env.filters["time_ago"] = time_ago
    app.jinja_env.filters["google_maps_url"] = google_maps_url
    app.jinja_env.filters["state_abbreviation"] = get_state_abbreviation
    app.jinja_env.filters["format_location"] = format_location_display
    app.jinja_env.filters["format_location_with_within"] = format_location_with_within
    app.jinja_env.filters["restaurant_location_display"] = restaurant_location_display
    app.jinja_env.filters["restaurant_table_location_display"] = restaurant_table_location_display
    app.jinja_env.filters["restaurant_address_display"] = restaurant_address_display
    app.jinja_env.filters["restaurant_address_only"] = restaurant_address_only
    app.jinja_env.filters["restaurant_address_with_maps"] = restaurant_address_with_maps
    app.jinja_env.filters["split"] = split_string
