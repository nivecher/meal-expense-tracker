"""
Application extensions module.

This module initializes and provides access to Flask extensions used throughout
the application.
"""

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

# Import SQLAlchemy instance from database module
from .database import db  # noqa: F401

# Initialize extensions
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

# Configure login view for Flask-Login
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
