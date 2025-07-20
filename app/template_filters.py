"""Custom template filters for the application."""

from datetime import datetime, timezone

from flask import Flask


def time_ago(value: datetime) -> str:
    """Format a datetime as a relative time string (e.g., '2 hours ago').

    Args:
        value: The datetime object to format

    Returns:
        str: A human-readable relative time string
    """
    if not value:
        return "Never"

    now = datetime.now(timezone.utc)
    diff = now - value

    # Calculate time differences
    seconds = int(diff.total_seconds())
    minutes = seconds // 60
    hours = minutes // 60
    days = diff.days

    if days > 365:
        years = days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    if days > 30:
        months = days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    if days > 0:
        return f"{days} day{'s' if days > 1 else ''} ago"
    if hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    return "Just now"


def init_app(app: Flask) -> None:
    """Initialize template filters for the Flask app.

    Args:
        app: The Flask application instance.
    """
    app.add_template_filter(time_ago, name="time_ago")
