from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, available_timezones

from flask import (
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
from app.extensions import db

from .forms import ChangePasswordForm, LoginForm, RegistrationForm


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login with standard Flask-Login patterns."""
    # If user is already logged in, redirect to next page or home
    if current_user.is_authenticated:
        next_page = request.args.get("next")
        if not next_page:
            next_page = url_for("main.index")
        elif next_page.startswith("http"):
            # Extract path from full URL for security
            from urllib.parse import urlparse

            parsed = urlparse(next_page)
            next_page = parsed.path or url_for("main.index")
        elif not next_page.startswith("/"):
            next_page = url_for("main.index")
        return redirect(next_page)

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)

            # Handle redirect after login
            next_page = request.form.get("next") or request.args.get("next")
            if not next_page:
                next_page = url_for("main.index")
            elif next_page.startswith("http"):
                # Extract path from full URL for security
                from urllib.parse import urlparse

                parsed = urlparse(next_page)
                next_page = parsed.path or url_for("main.index")
            elif not next_page.startswith("/"):
                next_page = url_for("main.index")

            flash("Login successful!", "success")
            # Ensure session is properly saved before redirect (important for Lambda/API Gateway)
            from flask import session

            session.permanent = True

            # Regenerate CSRF token after login for security (important for Lambda/API Gateway)
            from flask_wtf.csrf import generate_csrf

            session["_csrf_token"] = generate_csrf()

            return redirect(next_page)
        else:
            flash("Invalid username or password", "error")

    return render_template("auth/login.html", form=form, title="Login", now=datetime.now(timezone.utc))


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered user!")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form, title="Register", now=datetime.now(timezone.utc))


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    # Pre-populate username field for accessibility (hidden from user)
    if request.method == "GET":
        form.username.data = current_user.username
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            services.change_user_password(current_user, form.current_password.data, form.new_password.data)
            flash("Your password has been updated.")
            return redirect(url_for("main.index"))
        else:
            flash("Invalid password.")

    return render_template(
        "auth/change_password.html",
        form=form,
        title="Change Password",
        now=datetime.now(timezone.utc),
    )


def _handle_timezone_update():
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
    return jsonify({"success": True, "message": "Timezone updated successfully"})


def _handle_regular_profile_update():
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
        return redirect(url_for("auth.profile"))

    if current_user.bio and len(current_user.bio) > 500:
        flash("Bio is too long (max 500 characters)", "error")
        return redirect(url_for("auth.profile"))

    # Validate avatar URL if provided
    if current_user.avatar_url and len(current_user.avatar_url) > 255:
        flash("Avatar URL is too long (max 255 characters)", "error")
        return redirect(url_for("auth.profile"))

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
    return redirect(url_for("auth.profile"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
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
                return jsonify({"success": False, "message": "Failed to update timezone"}), 500
            flash("Failed to update profile. Please try again.", "error")
            current_app.logger.error(f"Profile update failed for user {current_user.id}: {e}")
            return redirect(url_for("auth.profile"))

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
        now=datetime.now(timezone.utc),
        current_time_user_tz=current_time_display,
        timezone_display=timezone_display,
        common_timezones=common_timezones,
        all_timezones=all_timezones,
        user_timezone=user_timezone,
    )


@bp.route("/api/detect-timezone", methods=["POST"])
@login_required
def detect_timezone():
    """API endpoint for timezone detection from coordinates."""
    try:
        data = request.get_json()
        lat = float(data.get("latitude", 0))
        lng = float(data.get("longitude", 0))

        # Basic timezone detection logic (simplified)
        # In production, you might want to use a more sophisticated
        # timezone boundary database or external service

        timezone_mappings = [
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

        detected_timezone = "UTC"  # Default fallback

        for mapping in timezone_mappings:
            bounds = mapping["bounds"]
            if lat <= bounds["north"] and lat >= bounds["south"] and lng >= bounds["west"] and lng <= bounds["east"]:
                detected_timezone = mapping["tz"]
                break

        # Validate the timezone
        try:
            ZoneInfo(detected_timezone)
        except Exception:
            detected_timezone = "UTC"

        return jsonify(
            {
                "success": True,
                "timezone": detected_timezone,
                "confidence": "medium",
                "method": "coordinate_lookup",
            }
        )

    except (ValueError, TypeError, KeyError):
        return (
            jsonify({"success": False, "error": "Invalid coordinates provided", "timezone": "UTC"}),
            400,
        )
    except Exception as e:
        current_app.logger.error(f"Timezone detection API error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Server error during timezone detection",
                    "timezone": "UTC",
                }
            ),
            500,
        )
