"""
Application factory for the Meal Expense Tracker API.

This module contains the application factory function and initializes Flask extensions.
"""

import os
from typing import Any, Dict, Optional

from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData

# Define a naming convention for database constraints
# This ensures consistent naming for database constraints across all tables
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Initialize extensions
db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
migrate = Migrate()


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        test_config: Optional test configuration to use

    Returns:
        Flask: The configured Flask application
    """
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    # Default configuration
    db_path = os.path.join(app.instance_path, "meal_expense_tracker.db")
    db_url = os.environ.get("DATABASE_URL") or f"sqlite:///{db_path}"

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or "dev",
        SQLALCHEMY_DATABASE_URI=db_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_pre_ping": True,
            "pool_recycle": 300,
        },
    )

    # Override with test config if provided
    if test_config is not None:
        app.config.update(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError as e:
        app.logger.error(f"Failed to create instance directory: {e}")

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from app.auth import bp as auth_bp
    from app.expenses import bp as expenses_bp
    from app.main import bp as main_bp
    from app.restaurants import bp as restaurants_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(restaurants_bp)
    app.register_blueprint(main_bp)

    # Initialize database
    with app.app_context():
        db.create_all()

        # Add any initial data if needed
        if not test_config and app.env == "development":
            _init_db_data()

    # Register error handlers
    _register_error_handlers(app)

    return app


def _init_db_data():
    """Initialize database with default data for development."""
    from werkzeug.security import generate_password_hash

    from app.auth.models import User

    # Create admin user if it doesn't exist
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", email="admin@example.com", password_hash=generate_password_hash("admin"))
        db.session.add(admin)
        db.session.commit()


def _register_error_handlers(app):
    """Register error handlers for the application."""
    from flask import jsonify
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500

    @app.errorhandler(HTTPException)
    def handle_exception(e):
        return jsonify({"error": e.description}), e.code
