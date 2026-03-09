"""Loyalty package for rewards program tracking."""

from flask import Blueprint

from .models import MerchantRewardsLink, RewardsAccount, RewardsProgram

bp = Blueprint("loyalty", __name__, url_prefix="/restaurants/merchants/loyalty")

from . import routes  # noqa: F401, E402

__all__ = ["RewardsProgram", "RewardsAccount", "MerchantRewardsLink", "bp"]
