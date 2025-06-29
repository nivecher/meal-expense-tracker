from __future__ import annotations

import logging

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.auth import bp
from app.auth.forms import ChangePasswordForm
from app.auth.models import User


@bp.route("/login", methods=["GET", "POST"])
def login():
    logger = logging.getLogger(__name__)
    logger.info("Login endpoint accessed")
    if current_user.is_authenticated:
        logger.info(f"User {current_user.username} already authenticated, redirecting to index")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        # Ensure CSRF token is validated
        if not request.form.get("csrf_token"):
            logger.warning("CSRF token missing from login form")
            flash("Security validation failed. Please try again.", "danger")
            return render_template("auth/login.html")
        username = request.form.get("username")
        password = request.form.get("password")
        logger.info(f"Login attempt for username: {username}")

        if not username or not password:
            logger.warning("Login failed: Missing username or password")
            flash("Please provide both username and password", "danger")
            return render_template("auth/login.html")

        logger.debug(f"Looking up user: {username}")
        try:
            stmt = select(User).where(User.username == username)
            user = db.session.scalar(stmt)

            if user is not None:
                logger.debug(f"User found: {user.username}")
                if user.check_password(password):
                    logger.info(f"Password check passed for user: {user.username}")
                    login_user(user)
                    flash("Welcome back!", "success")
                    next_page = request.args.get("next")
                    logger.info(f"Login successful, redirecting to: {next_page or 'index'}")
                    return redirect(next_page or url_for("main.index"))
                else:
                    logger.warning(f"Invalid password for user: {user.username}")
            else:
                logger.warning(f"User not found: {username}")
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            flash("An error occurred during login. Please try again.", "danger")
            return render_template("auth/login.html")

        flash("Invalid username or password", "danger")

    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out", "success")
    return redirect(url_for("auth.login"))


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change user password.

    Returns:
        Rendered template with change password form (GET) or redirect to profile (POST)
    """
    logger = logging.getLogger(__name__)
    logger.info("Change password endpoint called")
    form = ChangePasswordForm()

    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            logger.warning("Password change failed: Incorrect current password")
            flash("Current password is incorrect", "danger")
            return render_template("auth/change_password.html", form=form)

        try:
            logger.info("Updating user password")
            current_user.set_password(form.new_password.data)
            db.session.commit()
            logger.info("Password updated successfully")
            flash("Your password has been updated!", "success")
            return redirect(url_for("main.index"))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error updating password: {e}")
            flash("An error occurred while updating your password. Please try again.", "danger")

    return render_template("auth/change_password.html", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    logger = logging.getLogger(__name__)
    logger.info("Register endpoint called")

    if current_user.is_authenticated:
        logger.info("User already authenticated, redirecting to index")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        logger.info("Processing registration form")
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            logger.warning("Registration failed: Passwords do not match")
            flash("Passwords do not match", "danger")
            return render_template("auth/register.html", username=username)

        masked_username = "*" * len(username) if username else "None"
        masked_password = "*" * len(password) if password else "None"
        logger.debug(f"Form data - Username: {masked_username}, " f"Password: {masked_password}")

        if not username or not password:
            logger.warning("Registration failed: Missing required fields")
            flash("Please fill out all fields.", "danger")
            return render_template("auth/register.html", username=username)

        try:
            logger.debug("Checking for existing user")
            existing_user = db.session.scalars(select(User).where(User.username == username)).first()

            if existing_user is not None:
                logger.warning(f"Registration failed: Username '{username}' already exists")
                flash("Username already exists", "danger")
                return render_template("auth/register.html", username=username)

            logger.debug("Creating new user")
            user = User(username=username)
            user.set_password(password)

            logger.debug("Adding user to session")
            db.session.add(user)

            logger.debug("Committing transaction")
            db.session.commit()

            logger.info(f"Successfully created user: {username}")
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("auth.login"))

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error during registration: {str(e)}", exc_info=True)
            flash(f"Error creating user: {str(e)}", "error")
            return redirect(url_for("auth.register"))
        except Exception as e:
            db.session.rollback()
            logger.critical(f"Unexpected error during registration: {str(e)}", exc_info=True)
            flash("An unexpected error occurred. Please try again later.", "error")
            return redirect(url_for("auth.register"))

    logger.debug("Rendering registration form")
    return render_template("auth/register.html")
