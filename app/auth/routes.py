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
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Please fill out all fields.", "danger")
            return render_template("auth/register.html", username=username)

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return render_template("auth/register.html", username=username)

        try:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("auth.login"))
        except SQLAlchemyError:
            db.session.rollback()
            flash("Error creating user. Please try again.", "error")
            return redirect(url_for("auth.register"))

    return render_template("auth/register.html")
