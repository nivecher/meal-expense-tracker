"""User profile service functions."""

from typing import Any

from app.auth.models import User
from app.extensions import db


def update_user_profile(user: User, data: dict[str, Any]) -> User:
    """Update a user's profile."""
    for key, value in data.items():
        if key in ["username", "email"]:
            setattr(user, key, value)
    db.session.commit()
    return user
