from __future__ import annotations

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import bp, services
from app.auth.models import User
from app.extensions import db

from .forms import ChangePasswordForm, LoginForm, RegistrationForm


def _handle_login_failure():
    """Handle login failure for both AJAX and regular requests."""
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Invalid username or password",
                    "errors": {"form": ["Invalid username or password"]},
                }
            ),
            400,
        )

    flash("Invalid username or password", "error")
    return redirect(url_for("auth.login", next=request.args.get("next")))


def _handle_login_success(user, next_page):
    """Handle successful login for both AJAX and regular requests."""
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(
            {
                "success": True,
                "message": "Logged in successfully",
                "redirect": next_page,
                "user": {"id": user.id, "username": user.username, "email": user.email},
            }
        )

    return redirect(next_page)


def _handle_form_validation_errors(form):
    """Handle form validation errors for AJAX requests."""
    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        errors = {}
        if form.errors:
            for field, error_list in form.errors.items():
                errors[field] = error_list

        return jsonify({"success": False, "message": "Please correct the errors below", "errors": errors}), 400
    return None


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login.

    GET: Display the login form
    POST: Process login form submission
    """
    # If user is already logged in, redirect to the next page or home
    if current_user.is_authenticated:
        next_page = request.args.get("next")
        if not next_page or not next_page.startswith("/"):
            next_page = url_for("main.index")
        return redirect(next_page)

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            return _handle_login_failure()

        login_user(user, remember=form.remember_me.data)

        # Handle the 'next' parameter for redirection after login
        next_page = request.args.get("next")
        if not next_page or not next_page.startswith("/"):
            next_page = url_for("main.index")

        return _handle_login_success(user, next_page)

    # Handle AJAX validation errors
    validation_response = _handle_form_validation_errors(form)
    if validation_response:
        return validation_response

    from datetime import datetime, timezone

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
    from datetime import datetime, timezone

    return render_template("auth/register.html", form=form, title="Register", now=datetime.now(timezone.utc))


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            services.change_user_password(current_user, form.current_password.data, form.new_password.data)
            flash("Your password has been updated.")
            return redirect(url_for("main.index"))
        else:
            flash("Invalid password.")
    from datetime import datetime, timezone

    return render_template(
        "auth/change_password.html",
        form=form,
        title="Change Password",
        now=datetime.now(timezone.utc),
    )


@bp.route("/profile")
@login_required
def profile():
    """User profile page."""
    from datetime import datetime, timezone

    return render_template("auth/profile.html", title="Profile", now=datetime.now(timezone.utc))
