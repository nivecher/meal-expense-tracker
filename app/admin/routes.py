"""Admin routes for user management and system administration."""

import secrets
import string
from typing import Any, Dict

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func

from app.auth.models import User
from app.extensions import db
from app.utils.decorators import admin_required, db_transaction

# Create admin blueprint
bp = Blueprint("admin", __name__, url_prefix="/admin")


def generate_secure_password(length: int = 12) -> str:
    """Generate a secure random password.

    Args:
        length: Length of the password to generate

    Returns:
        A secure random password string
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password


def send_password_reset_email(user: User, new_password: str) -> bool:
    """Send password reset email to user.

    Args:
        user: User object to send email to
        new_password: The new password to send

    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        from app.services.email_service import is_email_enabled
        from app.services.email_service import send_password_reset_email as send_email

        # Check if email is enabled
        if not is_email_enabled():
            current_app.logger.info(
                f"Email disabled, logging password reset for user {user.username} ({user.email}): {new_password}"
            )
            return False

        # Try to send email
        email_sent = send_email(user.email, user.username, new_password)

        if not email_sent:
            # Fallback: log the password reset
            current_app.logger.warning(
                f"Email failed, logging password reset for user {user.username} ({user.email}): {new_password}"
            )

        return email_sent

    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email: {e}")
        # Fallback: log the password reset
        current_app.logger.info(f"Password reset for user {user.username} ({user.email}): {new_password}")
        return False


@bp.route("/")
@login_required
@admin_required
def dashboard():
    """Admin dashboard showing system overview."""
    try:
        # Get system statistics
        total_users = db.session.query(func.count(User.id)).scalar() or 0
        admin_users = db.session.query(func.count(User.id)).filter_by(is_admin=True).scalar() or 0
        active_users = db.session.query(func.count(User.id)).filter_by(is_active=True).scalar() or 0

        # Get recent users (last 10)
        recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

        stats = {
            "total_users": total_users,
            "admin_users": admin_users,
            "regular_users": total_users - admin_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
        }

        # Check email status
        from app.services.email_service import is_email_enabled

        email_enabled = is_email_enabled()

        return render_template(
            "admin/dashboard.html",
            title="Admin Dashboard",
            stats=stats,
            recent_users=recent_users,
            email_enabled=email_enabled,
        )

    except Exception as e:
        current_app.logger.error(f"Error loading admin dashboard: {e}")
        flash("Error loading admin dashboard", "danger")
        return redirect(url_for("main.index"))


@bp.route("/users")
@login_required
@admin_required
def list_users():
    """List all users with admin controls."""
    try:
        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        search = request.args.get("search", "", type=str).strip()
        admin_only = request.args.get("admin_only", False, type=bool)
        active_only = request.args.get("active_only", False, type=bool)

        # Build query
        query = User.query

        # Apply filters
        if search:
            query = query.filter(
                (User.username.ilike(f"%{search}%"))
                | (User.email.ilike(f"%{search}%"))
                | (User.first_name.ilike(f"%{search}%"))
                | (User.last_name.ilike(f"%{search}%"))
            )

        if admin_only:
            query = query.filter_by(is_admin=True)

        if active_only:
            query = query.filter_by(is_active=True)

        # Order by creation date (newest first)
        query = query.order_by(User.created_at.desc())

        # Paginate results
        users = query.paginate(page=page, per_page=per_page, error_out=False)

        return render_template(
            "admin/users.html",
            title="User Management",
            users=users,
            search=search,
            admin_only=admin_only,
            active_only=active_only,
        )

    except Exception as e:
        current_app.logger.error(f"Error loading users: {e}")
        flash("Error loading users", "danger")
        return redirect(url_for("admin.dashboard"))


@bp.route("/users/<int:user_id>")
@login_required
@admin_required
def view_user(user_id: int):
    """View detailed information about a specific user."""
    try:
        user = User.query.get_or_404(user_id)

        # Get user statistics
        stats = {
            "expense_count": user.expenses.count() if hasattr(user, "expenses") else 0,
            "restaurant_count": user.restaurants.count() if hasattr(user, "restaurants") else 0,
            "category_count": user.categories.count() if hasattr(user, "categories") else 0,
        }

        return render_template(
            "admin/user_detail.html", title=f"User: {user.get_display_name()}", user=user, stats=stats
        )

    except Exception as e:
        current_app.logger.error(f"Error loading user {user_id}: {e}")
        flash("Error loading user details", "danger")
        return redirect(url_for("admin.list_users"))


@bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
@admin_required
@db_transaction(success_message="Password reset successfully", error_message="Failed to reset password")
def reset_user_password(user_id: int):
    """Reset a user's password and email it to them."""
    try:
        user = User.query.get_or_404(user_id)

        # Generate new password
        new_password = generate_secure_password()

        # Update user's password
        user.set_password(new_password)
        db.session.add(user)

        # Send email with new password
        email_sent = send_password_reset_email(user, new_password)

        if email_sent:
            flash(f"Password reset successfully. New password sent to {user.email}", "success")
        else:
            flash(f"Password reset but email failed to send. New password: {new_password}", "warning")

        return redirect(url_for("admin.view_user", user_id=user_id))

    except Exception as e:
        current_app.logger.error(f"Error resetting password for user {user_id}: {e}")
        flash("Error resetting password", "danger")
        return redirect(url_for("admin.view_user", user_id=user_id))


@bp.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
@login_required
@admin_required
@db_transaction(success_message="User admin status updated", error_message="Failed to update admin status")
def toggle_user_admin(user_id: int):
    """Toggle admin status for a user."""
    try:
        user = User.query.get_or_404(user_id)

        # Prevent admin from removing their own admin status
        if user.id == current_user.id:
            flash("You cannot remove admin privileges from yourself", "warning")
            return redirect(url_for("admin.view_user", user_id=user_id))

        # Toggle admin status
        user.is_admin = not user.is_admin
        db.session.add(user)

        status = "granted" if user.is_admin else "removed"
        flash(f"Admin privileges {status} for {user.get_display_name()}", "success")

        return redirect(url_for("admin.view_user", user_id=user_id))

    except Exception as e:
        current_app.logger.error(f"Error toggling admin status for user {user_id}: {e}")
        flash("Error updating admin status", "danger")
        return redirect(url_for("admin.view_user", user_id=user_id))


@bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
@db_transaction(success_message="User active status updated", error_message="Failed to update active status")
def toggle_user_active(user_id: int):
    """Toggle active status for a user."""
    try:
        user = User.query.get_or_404(user_id)

        # Prevent admin from deactivating themselves
        if user.id == current_user.id:
            flash("You cannot deactivate your own account", "warning")
            return redirect(url_for("admin.view_user", user_id=user_id))

        # Toggle active status
        user.is_active = not user.is_active
        db.session.add(user)

        status = "activated" if user.is_active else "deactivated"
        flash(f"Account {status} for {user.get_display_name()}", "success")

        return redirect(url_for("admin.view_user", user_id=user_id))

    except Exception as e:
        current_app.logger.error(f"Error toggling active status for user {user_id}: {e}")
        flash("Error updating active status", "danger")
        return redirect(url_for("admin.view_user", user_id=user_id))


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
@db_transaction(success_message="User deleted successfully", error_message="Failed to delete user")
def delete_user(user_id: int):
    """Delete a user account and all related data."""
    try:
        user = User.query.get_or_404(user_id)

        # Prevent admin from deleting themselves
        if user.id == current_user.id:
            flash("You cannot delete your own account", "warning")
            return redirect(url_for("admin.view_user", user_id=user_id))

        # Store user info for confirmation message
        username = user.username
        display_name = user.get_display_name()

        # Count related data for confirmation message
        related_counts = {
            "expenses": user.expenses.count(),
            "restaurants": user.restaurants.count(),
            "categories": user.categories.count(),
        }
        total_related = sum(related_counts.values())

        # Delete the user (cascade will handle related data)
        db.session.delete(user)

        # Prepare success message
        if total_related > 0:
            flash(
                f"User '{display_name}' ({username}) and {total_related} related records deleted successfully",
                "success",
            )
        else:
            flash(f"User '{display_name}' ({username}) deleted successfully", "success")

        return redirect(url_for("admin.list_users"))

    except Exception as e:
        current_app.logger.error(f"Error deleting user {user_id}: {e}")
        flash("Error deleting user", "danger")
        return redirect(url_for("admin.view_user", user_id=user_id))


def _extract_user_form_data() -> Dict[str, Any]:
    """Extract and validate form data for user creation.

    Returns:
        Dictionary containing form data
    """
    return {
        "username": request.form.get("username", "").strip(),
        "email": request.form.get("email", "").strip(),
        "first_name": request.form.get("first_name", "").strip(),
        "last_name": request.form.get("last_name", "").strip(),
        "is_admin": request.form.get("is_admin") == "on",
        "is_active": request.form.get("is_active") == "on",
        "send_password_email": request.form.get("send_password_email") == "on",
    }


def _validate_user_form_data(form_data: Dict[str, Any]) -> tuple[bool, str]:
    """Validate user form data.

    Args:
        form_data: Dictionary containing form data

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not form_data["username"] or not form_data["email"]:
        return False, "Username and email are required"

    existing_user = User.query.filter(
        (User.username == form_data["username"]) | (User.email == form_data["email"])
    ).first()

    if existing_user:
        return False, "User with this username or email already exists"

    return True, ""


def _create_user_from_form_data(form_data: Dict[str, Any], password: str) -> User:
    """Create a new user from form data.

    Args:
        form_data: Dictionary containing form data
        password: Generated password for the user

    Returns:
        Created User object
    """
    user = User(
        username=form_data["username"],
        email=form_data["email"],
        first_name=form_data["first_name"] or None,
        last_name=form_data["last_name"] or None,
        is_admin=form_data["is_admin"],
        is_active=form_data["is_active"],
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # Get the user ID
    return user


def _handle_password_email(user: User, password: str, send_email: bool) -> None:
    """Handle sending password email to new user.

    Args:
        user: User object
        password: Generated password
        send_email: Whether to send email
    """
    if not send_email:
        flash(f"User created successfully. Password: {password}", "success")
        return

    try:
        from app.services.email_service import is_email_enabled, send_welcome_email

        if not is_email_enabled():
            flash(f"User created successfully. Password: {password} (Email disabled)", "success")
        else:
            email_sent = send_welcome_email(user.email, user.username, password)
            if email_sent:
                flash(f"User created and welcome email sent to {user.email}", "success")
            else:
                flash(f"User created but email failed. Password: {password}", "warning")
    except Exception as e:
        current_app.logger.error(f"Failed to send welcome email: {e}")
        flash(f"User created but email failed. Password: {password}", "warning")


@bp.route("/users/create", methods=["GET", "POST"])
@login_required
@admin_required
@db_transaction(success_message="User created successfully", error_message="Failed to create user")
def create_user():
    """Create a new user."""
    if request.method == "GET":
        return render_template("admin/create_user.html", title="Create User")

    try:
        # Extract and validate form data
        form_data = _extract_user_form_data()
        is_valid, error_message = _validate_user_form_data(form_data)

        if not is_valid:
            flash(error_message, "danger")
            return render_template("admin/create_user.html", title="Create User")

        # Generate password and create user
        password = generate_secure_password()
        user = _create_user_from_form_data(form_data, password)

        # Handle password email
        _handle_password_email(user, password, form_data["send_password_email"])

        return redirect(url_for("admin.view_user", user_id=user.id))

    except Exception as e:
        current_app.logger.error(f"Error creating user: {e}")
        flash("Error creating user", "danger")
        return render_template("admin/create_user.html", title="Create User")


@bp.route("/api/users/<int:user_id>/stats")
@login_required
@admin_required
def get_user_stats(user_id: int):
    """Get user statistics as JSON."""
    try:
        user = User.query.get_or_404(user_id)

        stats = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "expense_count": user.expenses.count() if hasattr(user, "expenses") else 0,
            "restaurant_count": user.restaurants.count() if hasattr(user, "restaurants") else 0,
            "category_count": user.categories.count() if hasattr(user, "categories") else 0,
        }

        return jsonify({"success": True, "data": stats})

    except Exception as e:
        current_app.logger.error(f"Error getting user stats for {user_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
