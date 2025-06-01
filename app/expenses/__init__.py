from flask import Blueprint

bp = Blueprint("expenses", __name__)

from app.expenses import routes  # noqa: E402
