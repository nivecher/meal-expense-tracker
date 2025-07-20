from flask import Blueprint

bp = Blueprint("api", __name__)

# Import routes to register them with the blueprint
from . import auth  # noqa: E402, F401
from . import routes  # noqa: E402, F401
