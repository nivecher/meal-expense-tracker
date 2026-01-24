from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timezone
from typing import Any, TypeVar, Union, cast
from zoneinfo import ZoneInfo, available_timezones

from flask import (
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import bp, services
from app.auth.models import User
from app.extensions import db, limiter

from .forms import ChangePasswordForm, LoginForm, RegistrationForm


def _is_safe_url(url: str | None) -> bool:
    """Check if a URL is safe for redirect (internal only, no external URLs).

    Args:
        url: The URL to validate

    Returns:
        True if the URL is safe for redirect, False otherwise
    """
    if not url:
        return False

    # Reject external URLs (http://, https://)
    if url.startswith(("http://", "https://")):
        return False

    # Reject protocol-relative URLs (//example.com)
    if url.startswith("//"):
        return False

    # Accept relative URLs that start with /
    if url.startswith("/"):
        # Additional validation: ensure no dangerous patterns
        # Reject URLs with query parameters that could be exploited
        # (We allow query params but validate the path itself)
        from urllib.parse import urlparse

        parsed = urlparse(url)
        # Only allow paths, not full URLs
        if parsed.netloc:
            return False
        return True

    return False


def _get_safe_redirect_url(next_url: str | None) -> str:
    """Get a safe redirect URL from user input, defaulting to home if invalid.

    Args:
        next_url: The URL from user input (query parameter or form field)

    Returns:
        A safe URL for redirect (always an internal route)
    """
    if next_url and _is_safe_url(next_url):
        return next_url
    return url_for("main.index")


def _exempt_get_requests() -> bool:
    """Exempt GET requests from rate limiting on login page."""
    return request.method == "GET"


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"], override_defaults=True, exempt_when=_exempt_get_requests)
def login() -> str | Response:
    """Handle user login with standard Flask-Login patterns.

    Rate limiting: Only POST requests (login attempts) are rate limited to 10 per minute.
    GET requests (viewing the login page) are exempt from rate limiting.
    """
    # Get next parameter from either query string (GET) or form data (POST)
    next_param = request.args.get("next") or request.form.get("next")

    # If user is already logged in, redirect to next page or home
    if current_user.is_authenticated:
        next_page = _get_safe_redirect_url(next_param)
        return cast(Response, redirect(next_page))  # noqa: S303

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = _get_safe_redirect_url(next_param)

            flash("Login successful!", "success")
            from flask import session

            session.permanent = form.remember_me.data
            from flask_wtf.csrf import generate_csrf

            session["_csrf_token"] = generate_csrf()

            return cast(Response, redirect(next_page))  # noqa: S303
        else:
            flash("Invalid username or password", "error")

    # Pass next parameter to template so it can be included in the form
    return render_template("auth/login.html", form=form, title="Login", now=datetime.now(UTC), next_url=next_param)


@bp.route("/logout")
@login_required
def logout() -> Response:
    logout_user()
    return cast(Response, redirect(url_for("main.index")))


@bp.route("/register", methods=["GET", "POST"])
def register() -> str | Response:
    if current_user.is_authenticated:
        return cast(Response, redirect(url_for("main.index")))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        password = form.password.data
        if password:
            user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered user!")
        return cast(Response, redirect(url_for("auth.login")))

    return render_template("auth/register.html", form=form, title="Register", now=datetime.now(UTC))


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password() -> str | Response:
    form = ChangePasswordForm()
    # Pre-populate username field for accessibility (hidden from user)
    if request.method == "GET":
        form.username.data = current_user.username
    if form.validate_on_submit():
        current_password = form.current_password.data
        new_password = form.new_password.data
        if current_password and new_password and current_user.check_password(current_password):
            services.change_user_password(current_user, current_password, new_password)
            flash("Your password has been updated.")
            return cast(Response, redirect(url_for("main.index")))
        else:
            flash("Invalid password.")

    return render_template(
        "auth/change_password.html",
        form=form,
        title="Change Password",
        now=datetime.now(UTC),
    )


def _handle_timezone_update() -> Response:
    """Handle timezone-only update via AJAX."""
    from app.utils.timezone_utils import normalize_timezone

    new_timezone = request.form.get("timezone", "UTC").strip()

    # Normalize and validate timezone (handles deprecated names like US/Central)
    normalized_tz = normalize_timezone(new_timezone)
    if not normalized_tz:
        normalized_tz = "UTC"
        current_app.logger.warning(f"Invalid timezone '{new_timezone}', defaulted to UTC")

    current_user.timezone = normalized_tz
    db.session.commit()

    current_app.logger.info(f"Timezone updated for user {current_user.id}: {normalized_tz} (from {new_timezone})")
    return cast(Response, jsonify({"success": True, "message": "Timezone updated successfully"}))


def _handle_regular_profile_update() -> Response:
    """Handle regular profile update."""
    current_user.first_name = request.form.get("first_name", "").strip() or None
    current_user.last_name = request.form.get("last_name", "").strip() or None
    current_user.display_name = request.form.get("display_name", "").strip() or None
    current_user.bio = request.form.get("bio", "").strip() or None
    current_user.phone = request.form.get("phone", "").strip() or None
    current_user.timezone = request.form.get("timezone", "UTC").strip()
    current_user.avatar_url = request.form.get("avatar_url", "").strip() or None

    # Basic validation
    if current_user.phone and len(current_user.phone) > 20:
        flash("Phone number is too long (max 20 characters)", "error")
        return cast(Response, redirect(url_for("auth.profile")))

    if current_user.bio and len(current_user.bio) > 500:
        flash("Bio is too long (max 500 characters)", "error")
        return cast(Response, redirect(url_for("auth.profile")))

    # Validate avatar URL if provided
    if current_user.avatar_url and len(current_user.avatar_url) > 255:
        flash("Avatar URL is too long (max 255 characters)", "error")
        return cast(Response, redirect(url_for("auth.profile")))

    # Validate and normalize timezone
    from app.utils.timezone_utils import normalize_timezone

    if current_user.timezone:
        normalized_tz = normalize_timezone(current_user.timezone)
        if not normalized_tz:
            current_user.timezone = "UTC"
            flash("Invalid timezone, defaulted to UTC", "warning")
        elif normalized_tz != current_user.timezone:
            # Update to normalized version if it was a deprecated name
            original_tz = current_user.timezone
            current_user.timezone = normalized_tz
            current_app.logger.info(f"Normalized timezone from {original_tz} to {normalized_tz}")

    db.session.commit()
    flash("Profile updated successfully!", "success")
    return cast(Response, redirect(url_for("auth.profile")))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile() -> str | Response:
    """User profile management page."""
    if request.method == "POST":
        try:
            # Check if this is a timezone-only update (AJAX)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" and "timezone" in request.form:
                return _handle_timezone_update()

            # Regular profile update
            return _handle_regular_profile_update()

        except Exception as e:
            db.session.rollback()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                response = cast(Response, jsonify({"success": False, "message": "Failed to update timezone"}))
                response.status_code = 500
                return response
            flash("Failed to update profile. Please try again.", "error")
            current_app.logger.error(f"Profile update failed for user {current_user.id}: {e}")
            return cast(Response, redirect(url_for("auth.profile")))

    # Get common timezones for the dropdown (using IANA timezone names)
    common_timezones_raw = [
        "UTC",
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Asia/Tokyo",
        "Asia/Shanghai",
        "Australia/Sydney",
    ]

    from app.utils.timezone_utils import (
        format_current_time_for_user,
        get_timezone_display_name,
        normalize_timezone,
    )

    # Get user's saved timezone, normalize if needed
    user_timezone = current_user.timezone or "UTC"
    user_timezone = normalize_timezone(user_timezone) or "UTC"

    # Update database if timezone was normalized (e.g., US/Central -> America/Chicago)
    if current_user.timezone != user_timezone:
        current_user.timezone = user_timezone
        db.session.commit()

    # Show current time in user's timezone

    current_time_display = format_current_time_for_user(user_timezone, "%B %d, %Y at %I:%M:%S %p")
    timezone_display = get_timezone_display_name(user_timezone)

    # Create timezone lists with display names
    common_timezones = [(tz, get_timezone_display_name(tz)) for tz in common_timezones_raw]
    all_timezones_raw = sorted(available_timezones())
    all_timezones = [(tz, get_timezone_display_name(tz)) for tz in all_timezones_raw]

    return render_template(
        "auth/profile.html",
        title="Profile",
        now=datetime.now(UTC),
        current_time_user_tz=current_time_display,
        timezone_display=timezone_display,
        common_timezones=common_timezones,
        all_timezones=all_timezones,
        user_timezone=user_timezone,
    )


def _get_timezone_mappings() -> list[dict[str, Any]]:
    """Get timezone mappings for coordinate-based detection.

    Returns:
        List of timezone mapping dictionaries with bounds and timezone names
    """
    return [
        # North America
        {
            "bounds": {"north": 71, "south": 25, "west": -130, "east": -114},
            "tz": "America/Los_Angeles",
        },
        {
            "bounds": {"north": 71, "south": 25, "west": -114, "east": -104},
            "tz": "America/Denver",
        },
        {
            "bounds": {"north": 71, "south": 25, "west": -104, "east": -80},
            "tz": "America/Chicago",
        },
        {
            "bounds": {"north": 71, "south": 25, "west": -80, "east": -60},
            "tz": "America/New_York",
        },
        # Europe
        {"bounds": {"north": 71, "south": 35, "west": -10, "east": 15}, "tz": "Europe/London"},
        {"bounds": {"north": 71, "south": 35, "west": 15, "east": 30}, "tz": "Europe/Berlin"},
        # Asia
        {"bounds": {"north": 71, "south": 10, "west": 75, "east": 105}, "tz": "Asia/Bangkok"},
        {"bounds": {"north": 71, "south": 10, "west": 105, "east": 135}, "tz": "Asia/Shanghai"},
        {"bounds": {"north": 71, "south": 25, "west": 135, "east": 180}, "tz": "Asia/Tokyo"},
        # Australia
        {
            "bounds": {"north": -10, "south": -45, "west": 110, "east": 155},
            "tz": "Australia/Sydney",
        },
    ]


def _detect_timezone_from_coordinates(lat: float, lng: float) -> str:
    """Detect timezone from latitude and longitude coordinates.

    Args:
        lat: Latitude coordinate
        lng: Longitude coordinate

    Returns:
        Detected timezone name, or "UTC" as fallback
    """
    timezone_mappings = _get_timezone_mappings()

    for mapping in timezone_mappings:
        if isinstance(mapping, dict):
            bounds = mapping.get("bounds", {})
            if isinstance(bounds, dict):
                if (
                    lat <= bounds.get("north", 90)
                    and lat >= bounds.get("south", -90)
                    and lng >= bounds.get("west", -180)
                    and lng <= bounds.get("east", 180)
                ):
                    tz_value = mapping.get("tz")
                    if isinstance(tz_value, str):
                        return tz_value

    return "UTC"  # Default fallback


def _validate_timezone(timezone: str) -> str:
    """Validate that a timezone string is valid.

    Args:
        timezone: Timezone name to validate

    Returns:
        Valid timezone name, or "UTC" if invalid
    """
    try:
        ZoneInfo(timezone)
        return timezone
    except Exception:
        return "UTC"


@bp.route("/api/detect-timezone", methods=["POST"])
@login_required
def detect_timezone() -> Response | tuple[Response, int]:
    """API endpoint for timezone detection from coordinates."""
    try:
        data = request.get_json()
        lat = float(data.get("latitude", 0))
        lng = float(data.get("longitude", 0))

        # Basic timezone detection logic (simplified)
        # In production, you might want to use a more sophisticated
        # timezone boundary database or external service
        detected_timezone = _detect_timezone_from_coordinates(lat, lng)
        detected_timezone = _validate_timezone(detected_timezone)

        return cast(
            Response,
            jsonify(
                {
                    "success": True,
                    "timezone": detected_timezone,
                    "confidence": "medium",
                    "method": "coordinate_lookup",
                }
            ),
        )

    except (ValueError, TypeError, KeyError):
        return (
            cast(Response, jsonify({"success": False, "error": "Invalid coordinates provided", "timezone": "UTC"})),
            400,
        )
    except Exception as e:
        current_app.logger.error(f"Timezone detection API error: {e}")
        return (
            cast(
                Response,
                jsonify(
                    {
                        "success": False,
                        "error": "Server error during timezone detection",
                        "timezone": "UTC",
                    }
                ),
            ),
            500,
        )
