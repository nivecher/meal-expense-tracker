from flask import Blueprint

bp = Blueprint("restaurants", __name__, url_prefix="/restaurants")

from app.restaurants import routes  # noqa: E402
