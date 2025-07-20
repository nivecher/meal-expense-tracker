"""Restaurants blueprint."""

from flask import Blueprint

# Initialize Blueprint with template folder
bp = Blueprint("restaurants", __name__, template_folder="templates", static_folder="static")


# Register template filters
@bp.app_template_filter("truncate")
def truncate_filter(s, length=255, end="..."):
    """Truncate a string to the specified length.

    Args:
        s: The input string to truncate
        length: Maximum length of the truncated string
        end: String to append if truncation occurs

    Returns:
        str: Truncated string with optional ending
    """
    if not s:
        return ""
    if len(s) <= length:
        return s
    return s[: length - len(end)] + end


@bp.app_template_filter("nl2br")
def nl2br_filter(s):
    """Convert newlines to <br> tags for HTML display.

    Args:
        s: Input string with newlines

    Returns:
        str: String with newlines replaced by <br> tags
    """
    if not s:
        return ""
    return s.replace("\n", "<br>")


# Import routes after blueprint creation to avoid circular imports
from . import routes  # noqa: E402
