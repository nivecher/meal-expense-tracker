"""Template filters for the application."""

from datetime import datetime, timezone

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


def init_app(app: Flask):
    """Register the filter with the Flask app.

    Args:
        app: The Flask application instance
    """
    app.jinja_env.filters["time_ago"] = time_ago
