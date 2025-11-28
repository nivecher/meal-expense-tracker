"""Authentication-related service functions."""

from typing import Tuple

from app.auth.models import User
from app.extensions import db


def change_user_password(user: User, old_password: str, new_password: str) -> tuple[bool, str]:
    """Change a user's password."""
    if not user.check_password(old_password):
        return False, "Invalid old password."
    user.set_password(new_password)
    db.session.commit()
    return True, "Password updated successfully."
