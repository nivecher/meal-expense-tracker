import logging
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app import db
from app.auth import bp
from app.auth.models import User
from sqlalchemy.exc import SQLAlchemyError


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Welcome back!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.index"))
        else:
            flash("Invalid username or password", "danger")

    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out", "success")
    return redirect(url_for("auth.login"))


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

        masked_username = "*" * len(username) if username else "None"
        masked_password = "*" * len(password) if password else "None"
        logger.debug(
            f"Form data - Username: {masked_username}, " f"Password: {masked_password}"
        )

        if not username or not password:
            logger.warning("Registration failed: Missing required fields")
            flash("Please fill out all fields.", "danger")
            return render_template("auth/register.html", username=username)

        try:
            logger.debug("Checking for existing user")
            if User.query.filter_by(username=username).first():
                logger.warning(
                    f"Registration failed: Username '{username}' already exists"
                )
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
            logger.critical(
                f"Unexpected error during registration: {str(e)}", exc_info=True
            )
            flash("An unexpected error occurred. Please try again later.", "error")
            return redirect(url_for("auth.register"))

    logger.debug("Rendering registration form")
    return render_template("auth/register.html")
