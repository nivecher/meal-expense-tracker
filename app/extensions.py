"""
Application extensions module.

This module initializes and provides access to Flask extensions used throughout
the application.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Initialize SQLAlchemy for database access
db = SQLAlchemy()

# Initialize Flask-Migrate for database migrations
migrate = Migrate()

# Initialize Flask-Login for user session management
login_manager = LoginManager()

# Configure login view for Flask-Login
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
