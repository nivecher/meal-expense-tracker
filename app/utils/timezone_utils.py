"""Timezone utility functions for the application.

This module provides timezone-aware date and time formatting utilities
that respect user timezone preferences.
"""

from datetime import datetime, timezone
from typing import Optional, Union

import pytz
from flask import current_app


def get_user_timezone(user_timezone: Optional[str] = None) -> pytz.timezone:
    """Get a pytz timezone object from user timezone string.

    Args:
        user_timezone: User's timezone string (e.g., 'America/New_York')

    Returns:
        pytz.timezone: The timezone object, defaults to UTC if invalid

    Raises:
        ValueError: If timezone string is invalid
    """
    if not user_timezone:
        return pytz.UTC

    try:
        return pytz.timezone(user_timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        current_app.logger.warning(f"Unknown timezone: {user_timezone}, falling back to UTC")
        return pytz.UTC


def convert_to_user_timezone(dt: datetime, user_timezone: Optional[str] = None) -> datetime:
    """Convert a datetime to the user's timezone.

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
    if not dt:
        return dt

    # Ensure datetime is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Get user's timezone
    user_tz = get_user_timezone(user_timezone)

    # Convert to user's timezone
    return dt.astimezone(user_tz)


def format_datetime_for_user(
    dt: datetime, user_timezone: Optional[str] = None, format_str: str = "%B %d, %Y at %I:%M %p"
) -> str:
    """Format a datetime for display in user's timezone.

    Args:
        dt: The datetime to format
        user_timezone: User's timezone string
        format_str: Python strftime format string

    Returns:
        str: Formatted datetime string in user's timezone

    Safety:
        - Validates all inputs
        - Handles None datetimes
        - Falls back to UTC on timezone errors
    """
    if not dt:
        return "Never"

    try:
        # Convert to user's timezone
        user_dt = convert_to_user_timezone(dt, user_timezone)

        # Format the datetime
        return user_dt.strftime(format_str)
    except Exception as e:
        current_app.logger.error(f"Error formatting datetime: {e}")
        return "Invalid date"


def format_date_for_user(
    dt: Union[datetime, str], user_timezone: Optional[str] = None, format_str: str = "%B %d, %Y"
) -> str:
    """Format a date for display in user's timezone.

    Args:
        dt: The datetime or date to format
        user_timezone: User's timezone string
        format_str: Python strftime format string

    Returns:
        str: Formatted date string in user's timezone
    """
    if not dt:
        return "Never"

    try:
        # Handle date strings
        if isinstance(dt, str):
            # Try to parse common date formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
                try:
                    dt = datetime.strptime(dt, fmt)
                    break
                except ValueError:
                    continue
            else:
                return "Invalid date"

        # Convert to user's timezone
        user_dt = convert_to_user_timezone(dt, user_timezone)

        # Format the date
        return user_dt.strftime(format_str)
    except Exception as e:
        current_app.logger.error(f"Error formatting date: {e}")
        return "Invalid date"


def get_current_time_in_user_timezone(user_timezone: Optional[str] = None) -> datetime:
    """Get current time in user's timezone.

    Args:
        user_timezone: User's timezone string

    Returns:
        datetime: Current time in user's timezone
    """
    now_utc = datetime.now(timezone.utc)
    return convert_to_user_timezone(now_utc, user_timezone)


def format_current_time_for_user(
    user_timezone: Optional[str] = None, format_str: str = "%B %d, %Y at %I:%M:%S %p %Z"
) -> str:
    """Format current time for display in user's timezone.

    Args:
        user_timezone: User's timezone string
        format_str: Python strftime format string

    Returns:
        str: Formatted current time string
    """
    current_time = get_current_time_in_user_timezone(user_timezone)
    return current_time.strftime(format_str)


def time_ago_for_user(dt: datetime, user_timezone: Optional[str] = None) -> str:
    """Calculate time ago relative to user's timezone.

    Args:
        dt: The datetime to calculate time since
        user_timezone: User's timezone string

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
        # Get current time in user's timezone
        now_user = get_current_time_in_user_timezone(user_timezone)

        # Convert input datetime to user's timezone
        dt_user = convert_to_user_timezone(dt, user_timezone)

        # Calculate difference
        diff = now_user - dt_user

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

    Args:
        timezone_str: The timezone string to validate

    Returns:
        bool: True if timezone is valid, False otherwise
    """
    try:
        pytz.timezone(timezone_str)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False


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
        tz = pytz.timezone(timezone_str)
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
