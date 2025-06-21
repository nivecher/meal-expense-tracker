from flask import Blueprint
from app.extensions import login_manager

bp = Blueprint("auth", __name__)

# Import models and routes after blueprint creation to avoid circular imports
from app.auth import models, routes  # noqa: E402

# Initialize the login manager with the user loader
models.init_login_manager(login_manager)
