"""
Application extensions module.

This module initializes and provides access to Flask extensions used throughout
the application.
"""

from flask_babel import Babel
from flask_bootstrap import Bootstrap
from flask_caching import Cache
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_restful import Api
from flask_session import Session
from flask_wtf.csrf import CSRFProtect

# Import SQLAlchemy instance from database module
from .database import db  # noqa: F401

# Initialize extensions
migrate = Migrate()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
cache = Cache()
csrf = CSRFProtect()
cors = CORS()
mail = Mail()
babel = Babel()
bootstrap = Bootstrap()
session = Session()
api = Api()

# Configure login view for Flask-Login
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
