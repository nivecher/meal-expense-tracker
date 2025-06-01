from flask import Blueprint

bp = Blueprint("restaurants", __name__)

from app.restaurants import routes  # noqa: E402
