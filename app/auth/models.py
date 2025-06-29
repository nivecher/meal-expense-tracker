from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from flask_login import UserMixin
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db

if TYPE_CHECKING:
    from app.expenses.models import Expense
    from app.restaurants.models import Restaurant


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(256))

    # Relationships
    expenses: Mapped[List["Expense"]] = relationship("Expense", back_populates="user", lazy="dynamic")
    restaurants: Mapped[List["Restaurant"]] = relationship("Restaurant", back_populates="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        """Set the user's password.

        Args:
            password: The plaintext password to hash and store
        """
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)

    def check_password(self, password: str) -> bool:
        """Verify the password against the stored hash.

        Args:
            password: The plaintext password to verify

        Returns:
            bool: True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


def init_login_manager(login_manager_instance) -> None:
    """Initialize the login manager with the user loader.

    Args:
        login_manager_instance: The Flask-Login LoginManager instance
    """

    @login_manager_instance.user_loader
    def load_user(user_id: str) -> Optional[User]:
        """Load a user by ID.

        Args:
            user_id: The user ID as a string

        Returns:
            Optional[User]: The User instance if found, None otherwise
        """
        return db.session.get(User, int(user_id))
