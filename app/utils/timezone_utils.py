"""Timezone utility functions for the application.

This module provides timezone-aware date and time formatting utilities
that use browser timezone for date/time entry and display.
"""

from datetime import UTC, datetime, timezone
from typing import Optional, Union
import urllib.parse
from zoneinfo import ZoneInfo

from flask import current_app, request

# Mapping from deprecated timezone names to IANA timezone names
DEPRECATED_TIMEZONE_MAP = {
    "US/Eastern": "America/New_York",
    "US/Central": "America/Chicago",
    "US/Mountain": "America/Denver",
    "US/Pacific": "America/Los_Angeles",
    "US/Alaska": "America/Anchorage",
    "US/Hawaii": "Pacific/Honolulu",
    "US/Arizona": "America/Phoenix",
    "US/Indiana-Starke": "America/Indiana/Knox",
    "US/Michigan": "America/Detroit",
}


def normalize_timezone(timezone_str: str | None) -> str | None:
    """Normalize timezone string to IANA timezone name.

    Converts deprecated timezone names (like US/Central) to modern IANA names
    (like America/Chicago). Also handles URL-encoded timezones.
    Returns None if timezone is invalid.

    Args:
        timezone_str: Timezone string to normalize (may be URL-encoded)

    Returns:
        Optional[str]: Normalized IANA timezone name, or None if invalid
    """
    if not timezone_str:
        return None

    # Decode URL encoding if present (e.g., America%2FChicago -> America/Chicago)
    timezone_str = urllib.parse.unquote(timezone_str)

    # Check if it's a deprecated timezone name
    normalized = DEPRECATED_TIMEZONE_MAP.get(timezone_str)
    if normalized:
        return normalized

    # Try to validate it's a valid IANA timezone
    try:
        ZoneInfo(timezone_str)
        return timezone_str
    except Exception:
        current_app.logger.warning(f"Invalid timezone: {timezone_str}")
        return None


def _get_timezone_from_form() -> str | None:
    """Get timezone from form data."""
    if hasattr(request, "form"):
        return request.form.get("browser_timezone")
    return None


def _get_timezone_from_json() -> str | None:
    """Get timezone from JSON data."""
    if not (hasattr(request, "content_type") and request.content_type):
        return None
    if "application/json" not in request.content_type:
        return None
    try:
        if hasattr(request, "json") and request.json:
            timezone = request.json.get("browser_timezone")
            return str(timezone) if timezone else None
    except Exception:  # nosec B110 - Intentional: gracefully handle malformed JSON
        pass
    return None


def _get_timezone_from_cookie() -> str | None:
    """Get timezone from cookie."""
    if hasattr(request, "cookies"):
        return request.cookies.get("browser_timezone")
    return None


def _get_timezone_from_header() -> str | None:
    """Get timezone from header."""
    if hasattr(request, "headers"):
        return request.headers.get("X-Browser-Timezone")
    return None


def get_browser_timezone() -> str | None:
    """Get browser timezone from request.

    Checks form data, JSON, cookies, and headers for browser timezone.
    Cookies are set by JavaScript on page load for form initialization.

    Returns:
        Optional[str]: Browser timezone string (e.g., 'America/New_York') or None
    """
    if not request:
        return None

    # Try to get from form data first (for form submissions)
    browser_tz = _get_timezone_from_form()
    if browser_tz:
        return browser_tz

    # Try to get from JSON data (for AJAX requests)
    browser_tz = _get_timezone_from_json()
    if browser_tz:
        return browser_tz

    # Try to get from cookies (set by JavaScript on page load for form initialization)
    browser_tz = _get_timezone_from_cookie()
    if browser_tz:
        return browser_tz

    # Try to get from headers (for API requests)
    browser_tz = _get_timezone_from_header()
    if browser_tz:
        return browser_tz

    return None


def get_browser_timezone_info() -> tuple[str, str]:
    """Get normalized browser timezone and display name in one call.

    This is a convenience function that combines:
    - Getting browser timezone from request
    - Normalizing it (handles deprecated names and URL encoding)
    - Getting the display name

    Returns:
        tuple[str, str]: (normalized_timezone, display_name)
        Both default to "UTC" if timezone cannot be determined
    """
    browser_timezone_raw = get_browser_timezone() or "UTC"
    browser_timezone = normalize_timezone(browser_timezone_raw) or "UTC"
    timezone_display = get_timezone_display_name(browser_timezone)
    return browser_timezone, timezone_display


def get_timezone(timezone_str: str | None = None) -> ZoneInfo:
    """Get a ZoneInfo timezone object from timezone string.

    If timezone_str is not provided, attempts to get browser timezone from request.
    Falls back to UTC if not found or invalid.
    Automatically normalizes deprecated timezone names to IANA names.

    Args:
        timezone_str: Timezone string (e.g., 'America/New_York' or 'US/Central'). If None, tries to get from request.

    Returns:
        ZoneInfo: The timezone object, defaults to UTC if invalid
    """
    # If no timezone provided, try to get from browser
    if not timezone_str:
        timezone_str = get_browser_timezone()

    if not timezone_str:
        return ZoneInfo("UTC")

    # Normalize deprecated timezone names to IANA names
    normalized_tz = normalize_timezone(timezone_str)
    if not normalized_tz:
        current_app.logger.warning(f"Unknown timezone: {timezone_str}, falling back to UTC")
        return ZoneInfo("UTC")

    try:
        return ZoneInfo(normalized_tz)
    except Exception:
        current_app.logger.warning(f"Failed to create ZoneInfo for: {normalized_tz}, falling back to UTC")
        return ZoneInfo("UTC")


def get_user_timezone(user_timezone: str | None = None) -> ZoneInfo:
    """Get a ZoneInfo timezone object from user timezone string.

    DEPRECATED: Use get_timezone() instead, which uses browser timezone.

    Args:
        user_timezone: User's timezone string (e.g., 'America/New_York')

    Returns:
        ZoneInfo: The timezone object, defaults to UTC if invalid
    """
    return get_timezone(user_timezone)


def convert_to_browser_timezone(dt: datetime, browser_timezone: str | None = None) -> datetime:
    """Convert a datetime to the browser's timezone.

    Args:
        dt: The datetime to convert
        browser_timezone: Browser timezone string. If None, attempts to get from request.

    Returns:
        datetime: The datetime converted to browser's timezone

    Safety:
        - Validates timezone string
        - Handles naive datetimes by assuming UTC
        - Falls back to UTC on invalid timezone
    """
    if not dt:
        return dt

    # Ensure datetime is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    # Get browser timezone
    browser_tz = get_timezone(browser_timezone)

    # Convert to browser timezone
    return dt.astimezone(browser_tz)


def convert_to_user_timezone(dt: datetime, user_timezone: str | None = None) -> datetime:
    """Convert a datetime to the user's timezone.

    DEPRECATED: Use convert_to_browser_timezone() instead.

    Args:
        dt: The datetime to convert
        user_timezone: User's timezone string

    Returns:
        datetime: The datetime converted to user's timezone

    Safety:
        - Validates timezone string
        - Handles naive datetimes by assuming UTC
        - Falls back to UTC on invalid timezone
    """
    return convert_to_browser_timezone(dt, user_timezone)


def format_datetime_for_user(
    dt: datetime, user_timezone: str | None = None, format_str: str = "%B %d, %Y at %I:%M %p"
) -> str:
    """Format a datetime for display in browser's timezone.

    Args:
        dt: The datetime to format
        user_timezone: Browser timezone string. If None, attempts to get from request.
        format_str: Python strftime format string

    Returns:
        str: Formatted datetime string in browser's timezone

    Safety:
        - Validates all inputs
        - Handles None datetimes
        - Falls back to UTC on timezone errors
    """
    if not dt:
        return "Never"

    try:
        # Convert to browser's timezone
        browser_dt = convert_to_browser_timezone(dt, user_timezone)

        # Format the datetime
        return browser_dt.strftime(format_str)
    except Exception as e:
        current_app.logger.error(f"Error formatting datetime: {e}")
        return "Invalid date"


def format_datetime_with_timezone_abbr(
    dt: datetime, user_timezone: str | None = None, format_str: str = "%I:%M %p"
) -> str:
    """Format a datetime with timezone abbreviation in RFC format.

    Args:
        dt: The datetime to format
        user_timezone: Browser timezone string. If None, attempts to get from request.
        format_str: Python strftime format string for the time part

    Returns:
        str: Formatted datetime string with timezone abbreviation (e.g., "2:30 PM CST")

    Safety:
        - Validates all inputs
        - Handles None datetimes
        - Falls back to UTC on timezone errors
    """
    if not dt:
        return "Never"

    try:
        # Get browser timezone
        if not user_timezone:
            user_timezone = get_browser_timezone()

        # Normalize timezone
        normalized_tz = normalize_timezone(user_timezone) if user_timezone else None
        if not normalized_tz:
            normalized_tz = "UTC"

        # Convert to browser's timezone
        browser_tz = ZoneInfo(normalized_tz)
        browser_dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(browser_tz)

        # Format the datetime
        time_str = browser_dt.strftime(format_str)

        # Get timezone abbreviation (RFC format)
        tz_abbr = browser_dt.strftime("%Z")
        if not tz_abbr:
            # Fallback to offset if abbreviation not available
            offset = browser_dt.strftime("%z")
            tz_abbr = offset if offset else "UTC"

        return f"{time_str} {tz_abbr}"
    except Exception as e:
        current_app.logger.error(f"Error formatting datetime with timezone: {e}")
        return "Invalid date"


def format_date_for_user(dt: datetime | str, user_timezone: str | None = None, format_str: str = "%B %d, %Y") -> str:
    """Format a date for display in browser's timezone.

    Args:
        dt: The datetime or date to format
        user_timezone: Browser timezone string. If None, attempts to get from request.
        format_str: Python strftime format string

    Returns:
        str: Formatted date string in browser's timezone
    """
    if not dt:
        return "Never"

    try:
        # Handle date strings
        if isinstance(dt, str):
            # Try to parse common date formats
            dt_str = dt
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
                try:
                    dt = datetime.strptime(dt_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                return "Invalid date"

        # Convert to browser's timezone
        browser_dt = convert_to_browser_timezone(dt, user_timezone)

        # Format the date
        return browser_dt.strftime(format_str)
    except Exception as e:
        current_app.logger.error(f"Error formatting date: {e}")
        return "Invalid date"


def get_current_time_in_browser_timezone(browser_timezone: str | None = None) -> datetime:
    """Get current time in browser's timezone.

    Args:
        browser_timezone: Browser timezone string. If None, attempts to get from request.

    Returns:
        datetime: Current time in browser's timezone
    """
    now_utc = datetime.now(UTC)
    return convert_to_browser_timezone(now_utc, browser_timezone)


def get_current_time_in_user_timezone(user_timezone: str | None = None) -> datetime:
    """Get current time in user's timezone.

    DEPRECATED: Use get_current_time_in_browser_timezone() instead.

    Args:
        user_timezone: User's timezone string

    Returns:
        datetime: Current time in user's timezone
    """
    return get_current_time_in_browser_timezone(user_timezone)


def format_current_time_for_user(
    user_timezone: str | None = None, format_str: str = "%B %d, %Y at %I:%M:%S %p %Z"
) -> str:
    """Format current time for display in browser's timezone.

    Args:
        user_timezone: Browser timezone string. If None, attempts to get from request.
        format_str: Python strftime format string

    Returns:
        str: Formatted current time string
    """
    current_time = get_current_time_in_browser_timezone(user_timezone)
    return current_time.strftime(format_str)


def time_ago_for_user(dt: datetime, user_timezone: str | None = None) -> str:
    """Calculate time ago relative to browser's timezone.

    Args:
        dt: The datetime to calculate time since
        user_timezone: Browser timezone string. If None, attempts to get from request.

    Returns:
        str: A human-readable relative time string

    Safety:
        - Validates input datetime
        - Handles timezone conversion safely
        - Returns meaningful fallback strings
    """
    if not dt:
        return "Never"

    try:
        # Get current time in browser's timezone
        now_browser = get_current_time_in_browser_timezone(user_timezone)

        # Convert input datetime to browser's timezone
        dt_browser = convert_to_browser_timezone(dt, user_timezone)

        # Calculate difference
        diff = now_browser - dt_browser

        # Calculate time differences
        seconds = int(diff.total_seconds())
        minutes = seconds // 60
        hours = minutes // 60
        days = diff.days

        if days > 365:
            years = days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        elif days > 30:
            months = days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif days > 0:
            return f"{days} day{'s' if days > 1 else ''} ago"
        elif hours > 0:
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif minutes > 0:
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"

    except Exception as e:
        current_app.logger.error(f"Error calculating time ago: {e}")
        return "Unknown time"


def is_timezone_valid(timezone_str: str) -> bool:
    """Check if a timezone string is valid.

    Validates both IANA timezone names and deprecated names (which are normalized).

    Args:
        timezone_str: The timezone string to validate

    Returns:
        bool: True if timezone is valid (or can be normalized), False otherwise
    """
    if not timezone_str:
        return False

    normalized = normalize_timezone(timezone_str)
    return normalized is not None


def get_timezone_display_name(timezone_str: str) -> str:
    """Get a human-readable display name for a timezone.

    Args:
        timezone_str: The timezone string (e.g., 'America/New_York')

    Returns:
        str: Human-readable timezone name
    """
    if not timezone_str:
        return "UTC"

    try:
        tz = ZoneInfo(timezone_str)
        now = datetime.now(tz)

        # Get timezone abbreviation (e.g., EST, PST)
        tz_abbr = now.strftime("%Z")

        # Create display name
        display_name = timezone_str.replace("_", " ")
        if tz_abbr:
            display_name += f" ({tz_abbr})"

        return display_name
    except Exception:
        return timezone_str.replace("_", " ")


def get_timezone_abbreviation(timezone_str: str) -> str:
    """Get just the timezone abbreviation (e.g., CST, EST, PST).

    Args:
        timezone_str: The timezone string (e.g., 'America/New_York')

    Returns:
        str: Timezone abbreviation or UTC if unavailable
    """
    if not timezone_str:
        return "UTC"

    try:
        tz = ZoneInfo(timezone_str)
        now = datetime.now(tz)

        # Get timezone abbreviation (e.g., EST, PST, CST)
        tz_abbr = now.strftime("%Z")
        if tz_abbr:
            return tz_abbr

        # Fallback to offset if abbreviation not available
        offset = now.strftime("%z")
        if offset:
            return offset

        return "UTC"
    except Exception:
        return "UTC"
